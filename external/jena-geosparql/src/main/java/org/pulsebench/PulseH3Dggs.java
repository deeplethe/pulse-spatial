package org.pulsebench;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.uber.h3core.H3Core;
import com.uber.h3core.util.LatLng;
import org.apache.jena.datatypes.TypeMapper;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.geosparql.implementation.GeometryWrapper;
import org.apache.jena.geosparql.implementation.UnitsOfMeasure;
import org.apache.jena.geosparql.implementation.vocabulary.Unit_URI;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.sparql.engine.binding.Binding;
import org.apache.jena.sparql.expr.Expr;
import org.apache.jena.sparql.expr.ExprEvalException;
import org.apache.jena.sparql.expr.NodeValue;
import org.apache.jena.sparql.expr.aggregate.Accumulator;
import org.apache.jena.sparql.expr.aggregate.AggCustom;
import org.apache.jena.sparql.expr.aggregate.AggregateRegistry;
import org.apache.jena.sparql.function.FunctionBase1;
import org.apache.jena.sparql.function.FunctionBase2;
import org.apache.jena.sparql.function.FunctionBase3;
import org.apache.jena.sparql.function.FunctionEnv;
import org.apache.jena.sparql.function.FunctionRegistry;
import org.locationtech.jts.algorithm.MinimumBoundingCircle;
import org.locationtech.jts.algorithm.hull.ConcaveHull;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.CoordinateFilter;
import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.geom.GeometryCollection;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.operation.union.UnaryUnionOp;

/**
 * Executable H3 profile for the GeoSPARQL 1.1 DGGS conformance class.
 *
 * <p>The profile literal is {@code <https://h3geo.org/> CELL (id)} or
 * {@code CELLS (id ...)}.  GeoSPARQL operations use the polygonal union of
 * the addressed H3 cells. Geometry-valued results are covered at the input
 * resolution using H3 centre containment. This declared finite-resolution
 * interpretation is deliberately isolated behind the {@code --dggs-profile}
 * harness option.</p>
 */
public final class PulseH3Dggs {
    public static final String PROFILE = "https://h3geo.org/";

    private static final String GEOF =
        "http://www.opengis.net/def/function/geosparql/";
    private static final String DGGS =
        "http://www.opengis.net/ont/geosparql#dggsLiteral";
    private static final String SF = "http://www.opengis.net/ont/sf#";
    private static final String SQUARE_METRE =
        "http://www.opengis.net/def/uom/OGC/1.0/squareMetre";
    private static final String SQUARE_KILOMETRE =
        "http://www.opengis.net/def/uom/OGC/1.0/squareKilometre";
    private static final int DEFAULT_RESOLUTION = 9;
    private static final double CONCAVE_HULL_RATIO = 0.5;
    private static final Pattern LITERAL = Pattern.compile(
        "^<([^>]+)>\\s+(CELL|CELLS)\\s*\\(([^)]*)\\)\\s*$"
    );
    private static final GeometryFactory GEOMETRIES = new GeometryFactory();
    private static final H3Core H3 = loadH3();

    private PulseH3Dggs() {}

    public static void registerProfile() {
        FunctionRegistry functions = FunctionRegistry.get();
        registerUnary(functions, "boundary", UnaryMode.BOUNDARY);
        registerUnary(functions, "boundingCircle", UnaryMode.BOUNDING_CIRCLE);
        registerUnary(functions, "centroid", UnaryMode.CENTROID);
        registerUnary(functions, "convexHull", UnaryMode.CONVEX_HULL);
        registerUnary(functions, "concaveHull", UnaryMode.CONCAVE_HULL);
        registerUnary(functions, "coordinateDimension", UnaryMode.COORDINATE_DIMENSION);
        registerUnary(functions, "dimension", UnaryMode.DIMENSION);
        registerUnary(functions, "envelope", UnaryMode.ENVELOPE);
        registerUnary(functions, "geometryType", UnaryMode.GEOMETRY_TYPE);
        registerUnary(functions, "is3D", UnaryMode.IS_3D);
        registerUnary(functions, "isEmpty", UnaryMode.IS_EMPTY);
        registerUnary(functions, "isMeasured", UnaryMode.IS_MEASURED);
        registerUnary(functions, "isSimple", UnaryMode.IS_SIMPLE);
        registerUnary(functions, "spatialDimension", UnaryMode.SPATIAL_DIMENSION);
        registerUnary(functions, "getSRID", UnaryMode.GET_SRID);
        registerUnary(functions, "metricLength", UnaryMode.METRIC_LENGTH);
        registerUnary(functions, "metricPerimeter", UnaryMode.METRIC_PERIMETER);
        registerUnary(functions, "metricArea", UnaryMode.METRIC_AREA);
        registerUnary(functions, "maxX", UnaryMode.MAX_X);
        registerUnary(functions, "maxY", UnaryMode.MAX_Y);
        registerUnary(functions, "maxZ", UnaryMode.MAX_Z);
        registerUnary(functions, "minX", UnaryMode.MIN_X);
        registerUnary(functions, "minY", UnaryMode.MIN_Y);
        registerUnary(functions, "minZ", UnaryMode.MIN_Z);
        registerUnary(functions, "numGeometries", UnaryMode.NUM_GEOMETRIES);

        registerBinaryGeometry(functions, "difference", BinaryMode.DIFFERENCE);
        registerBinaryGeometry(functions, "intersection", BinaryMode.INTERSECTION);
        registerBinaryGeometry(functions, "symDifference", BinaryMode.SYM_DIFFERENCE);
        registerBinaryGeometry(functions, "union", BinaryMode.UNION);
        functions.put(GEOF + "metricBuffer", uri -> new MetricBuffer());
        functions.put(GEOF + "buffer", uri -> new Buffer());
        functions.put(GEOF + "metricDistance", uri -> new MetricDistance());
        functions.put(GEOF + "distance", uri -> new Distance());
        functions.put(GEOF + "transform", uri -> new Transform());
        functions.put(GEOF + "length", uri -> new UnitMeasure(MeasureMode.LENGTH));
        functions.put(GEOF + "perimeter", uri -> new UnitMeasure(MeasureMode.PERIMETER));
        functions.put(GEOF + "area", uri -> new UnitMeasure(MeasureMode.AREA));
        functions.put(GEOF + "geometryN", uri -> new GeometryN());
        functions.put(GEOF + "asDGGS", uri -> new AsDggs());

        registerAggregate("aggBoundingBox", AggregateMode.BOUNDING_BOX);
        registerAggregate("aggBoundingCircle", AggregateMode.BOUNDING_CIRCLE);
        registerAggregate("aggCentroid", AggregateMode.CENTROID);
        registerAggregate("aggConcaveHull", AggregateMode.CONCAVE_HULL);
        registerAggregate("aggConvexHull", AggregateMode.CONVEX_HULL);
        registerAggregate("aggUnion", AggregateMode.UNION);
    }

    private static H3Core loadH3() {
        try {
            return H3Core.newInstance();
        } catch (IOException error) {
            throw new ExceptionInInitializerError(error);
        }
    }

    private static void registerUnary(
        FunctionRegistry registry,
        String localName,
        UnaryMode mode
    ) {
        registry.put(GEOF + localName, uri -> new UnaryFunction(mode));
    }

    private static void registerBinaryGeometry(
        FunctionRegistry registry,
        String localName,
        BinaryMode mode
    ) {
        registry.put(GEOF + localName, uri -> new BinaryGeometry(mode));
    }

    private static void registerAggregate(String localName, AggregateMode mode) {
        AggregateRegistry.register(
            GEOF + localName,
            (aggregate, distinct) -> new DggsAccumulator(aggregate, distinct, mode)
        );
    }

    private enum UnaryMode {
        BOUNDARY,
        BOUNDING_CIRCLE,
        CENTROID,
        CONVEX_HULL,
        CONCAVE_HULL,
        COORDINATE_DIMENSION,
        DIMENSION,
        ENVELOPE,
        GEOMETRY_TYPE,
        IS_3D,
        IS_EMPTY,
        IS_MEASURED,
        IS_SIMPLE,
        SPATIAL_DIMENSION,
        GET_SRID,
        METRIC_LENGTH,
        METRIC_PERIMETER,
        METRIC_AREA,
        MAX_X,
        MAX_Y,
        MAX_Z,
        MIN_X,
        MIN_Y,
        MIN_Z,
        NUM_GEOMETRIES
    }

    private static final class UnaryFunction extends FunctionBase1 {
        private final UnaryMode mode;

        private UnaryFunction(UnaryMode mode) {
            this.mode = mode;
        }

        @Override
        public NodeValue exec(NodeValue value) {
            try {
                DggsValue source = parse(value);
                Geometry geometry = source.geometry();
                return switch (mode) {
                    case BOUNDARY -> dggs(geometry.getBoundary(), source.resolution());
                    case BOUNDING_CIRCLE -> dggs(
                        new MinimumBoundingCircle(geometry).getCircle(),
                        source.resolution()
                    );
                    case CENTROID -> dggs(geometry.getCentroid(), source.resolution());
                    case CONVEX_HULL -> dggs(geometry.convexHull(), source.resolution());
                    case CONCAVE_HULL -> dggs(
                        ConcaveHull.concaveHullByLengthRatio(
                            geometry,
                            CONCAVE_HULL_RATIO
                        ),
                        source.resolution()
                    );
                    case COORDINATE_DIMENSION -> NodeValue.makeInteger(2);
                    case DIMENSION -> NodeValue.makeInteger(geometry.getDimension());
                    case ENVELOPE -> dggs(
                        GEOMETRIES.toGeometry(geometry.getEnvelopeInternal()),
                        source.resolution()
                    );
                    case GEOMETRY_TYPE -> anyUri(SF + geometry.getGeometryType());
                    case IS_3D, IS_MEASURED -> NodeValue.FALSE;
                    case IS_EMPTY -> NodeValue.makeBoolean(geometry.isEmpty());
                    case IS_SIMPLE -> NodeValue.makeBoolean(geometry.isSimple());
                    case SPATIAL_DIMENSION -> NodeValue.makeInteger(2);
                    case GET_SRID -> anyUri(PROFILE);
                    case METRIC_LENGTH -> NodeValue.makeDouble(metricLength(geometry));
                    case METRIC_PERIMETER -> NodeValue.makeDouble(metricPerimeter(geometry));
                    case METRIC_AREA -> NodeValue.makeDouble(metricGeometry(geometry).getArea());
                    case MAX_X -> NodeValue.makeDouble(geometry.getEnvelopeInternal().getMaxX());
                    case MAX_Y -> NodeValue.makeDouble(geometry.getEnvelopeInternal().getMaxY());
                    case MAX_Z, MIN_Z -> NodeValue.makeDouble(0.0);
                    case MIN_X -> NodeValue.makeDouble(geometry.getEnvelopeInternal().getMinX());
                    case MIN_Y -> NodeValue.makeDouble(geometry.getEnvelopeInternal().getMinY());
                    case NUM_GEOMETRIES -> NodeValue.makeInteger(
                        geometry.getNumGeometries()
                    );
                };
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private enum BinaryMode { DIFFERENCE, INTERSECTION, SYM_DIFFERENCE, UNION }

    private static final class BinaryGeometry extends FunctionBase2 {
        private final BinaryMode mode;

        private BinaryGeometry(BinaryMode mode) {
            this.mode = mode;
        }

        @Override
        public NodeValue exec(NodeValue leftValue, NodeValue rightValue) {
            try {
                DggsValue left = parse(leftValue);
                DggsValue right = parse(rightValue);
                requireResolution(left, right);
                Geometry result = switch (mode) {
                    case DIFFERENCE -> left.geometry().difference(right.geometry());
                    case INTERSECTION -> left.geometry().intersection(right.geometry());
                    case SYM_DIFFERENCE -> left.geometry().symDifference(right.geometry());
                    case UNION -> left.geometry().union(right.geometry());
                };
                return dggs(result, left.resolution());
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private static final class MetricBuffer extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue value, NodeValue radius) {
            return buffer(value, radius.getDouble(), Unit_URI.METRE_URL);
        }
    }

    private static final class Buffer extends FunctionBase3 {
        @Override
        public NodeValue exec(NodeValue value, NodeValue radius, NodeValue units) {
            return buffer(value, radius.getDouble(), lexical(units));
        }
    }

    private static NodeValue buffer(NodeValue value, double radius, String unit) {
        try {
            DggsValue source = parse(value);
            double metres = UnitsOfMeasure.conversion(
                radius,
                unit,
                Unit_URI.METRE_URL
            );
            LocalFrame frame = LocalFrame.forGeometry(source.geometry());
            Geometry projected = frame.project(source.geometry());
            return dggs(frame.unproject(projected.buffer(metres)), source.resolution());
        } catch (Exception error) {
            throw failure(error);
        }
    }

    private static final class MetricDistance extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue left, NodeValue right) {
            return NodeValue.makeDouble(distanceMetres(left, right));
        }
    }

    private static final class Distance extends FunctionBase3 {
        @Override
        public NodeValue exec(NodeValue left, NodeValue right, NodeValue unit) {
            return NodeValue.makeDouble(
                UnitsOfMeasure.conversion(
                    distanceMetres(left, right),
                    Unit_URI.METRE_URL,
                    lexical(unit)
                )
            );
        }
    }

    private static double distanceMetres(NodeValue leftValue, NodeValue rightValue) {
        try {
            DggsValue left = parse(leftValue);
            DggsValue right = parse(rightValue);
            requireResolution(left, right);
            Geometry combined = UnaryUnionOp.union(
                List.of(left.geometry(), right.geometry())
            );
            LocalFrame frame = LocalFrame.forGeometry(combined);
            return frame.project(left.geometry()).distance(
                frame.project(right.geometry())
            );
        } catch (Exception error) {
            throw failure(error);
        }
    }

    private static final class Transform extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue value, NodeValue target) {
            if (!PROFILE.equals(lexical(target))) {
                throw new ExprEvalException(
                    "The H3 profile supports identity transform to " + PROFILE
                );
            }
            parse(value);
            return value;
        }
    }

    private enum MeasureMode { LENGTH, PERIMETER, AREA }

    private static final class UnitMeasure extends FunctionBase2 {
        private final MeasureMode mode;

        private UnitMeasure(MeasureMode mode) {
            this.mode = mode;
        }

        @Override
        public NodeValue exec(NodeValue value, NodeValue unitValue) {
            try {
                Geometry geometry = parse(value).geometry();
                String unit = lexical(unitValue);
                double metric = switch (mode) {
                    case LENGTH -> metricLength(geometry);
                    case PERIMETER -> metricPerimeter(geometry);
                    case AREA -> metricGeometry(geometry).getArea();
                };
                if (mode == MeasureMode.AREA) {
                    return NodeValue.makeDouble(convertSquareMetres(metric, unit));
                }
                return NodeValue.makeDouble(
                    UnitsOfMeasure.conversion(metric, Unit_URI.METRE_URL, unit)
                );
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private static final class GeometryN extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue value, NodeValue indexValue) {
            try {
                DggsValue source = parse(value);
                int index = indexValue.getInteger().intValueExact();
                if (index < 1 || index > source.geometry().getNumGeometries()) {
                    throw new ExprEvalException("geometryN index is one-based");
                }
                return dggs(
                    source.geometry().getGeometryN(index - 1),
                    source.resolution()
                );
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private static final class AsDggs extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue value, NodeValue profile) {
            if (!PROFILE.equals(lexical(profile))) {
                throw new ExprEvalException("Unsupported DGGS profile: " + lexical(profile));
            }
            Node node = value.asNode();
            if (node.isLiteral() && DGGS.equals(node.getLiteralDatatypeURI())) {
                parse(value);
                return value;
            }
            try {
                GeometryWrapper source = GeometryWrapper.extract(value);
                Geometry geometry = source.getXYGeometry();
                if (!source.getSrsInfo().isGeographic()) {
                    geometry = source.transform(
                        "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                    ).getXYGeometry();
                }
                return dggs(geometry, DEFAULT_RESOLUTION);
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private enum AggregateMode {
        BOUNDING_BOX,
        BOUNDING_CIRCLE,
        CENTROID,
        CONCAVE_HULL,
        CONVEX_HULL,
        UNION
    }

    private static final class DggsAccumulator implements Accumulator {
        private final List<Expr> arguments;
        private final boolean distinct;
        private final AggregateMode mode;
        private final List<Geometry> geometries = new ArrayList<>();
        private final Set<Node> seen = new HashSet<>();
        private int resolution = -1;
        private double ratio = CONCAVE_HULL_RATIO;

        private DggsAccumulator(
            AggCustom aggregate,
            boolean distinct,
            AggregateMode mode
        ) {
            this.arguments = List.copyOf(aggregate.getExprList().getList());
            this.distinct = distinct;
            this.mode = mode;
        }

        @Override
        public void accumulate(Binding binding, FunctionEnv environment) {
            try {
                NodeValue value = arguments.get(0).eval(binding, environment);
                if (distinct && !seen.add(value.asNode())) {
                    return;
                }
                DggsValue parsed = parse(value);
                if (resolution < 0) {
                    resolution = parsed.resolution();
                } else if (resolution != parsed.resolution()) {
                    throw new ExprEvalException("Mixed H3 resolutions in aggregate");
                }
                geometries.add(parsed.geometry());
                if (arguments.size() > 1) {
                    ratio = arguments.get(1).eval(binding, environment).getDouble();
                }
            } catch (ExprEvalException error) {
                // SPARQL aggregates ignore expression errors and unbound rows.
            }
        }

        @Override
        public NodeValue getValue() {
            if (geometries.isEmpty()) {
                return null;
            }
            Geometry union = UnaryUnionOp.union(geometries);
            Geometry result = switch (mode) {
                case BOUNDING_BOX -> GEOMETRIES.toGeometry(union.getEnvelopeInternal());
                case BOUNDING_CIRCLE -> new MinimumBoundingCircle(union).getCircle();
                case CENTROID -> union.getCentroid();
                case CONCAVE_HULL -> ConcaveHull.concaveHullByLengthRatio(union, ratio);
                case CONVEX_HULL -> union.convexHull();
                case UNION -> union;
            };
            return dggs(result, resolution);
        }
    }

    private record DggsValue(List<String> cells, int resolution, Geometry geometry) {}

    private static DggsValue parse(NodeValue value) {
        Node node = value.asNode();
        if (!node.isLiteral() || !DGGS.equals(node.getLiteralDatatypeURI())) {
            throw new ExprEvalException("Expected geo:dggsLiteral");
        }
        String text = node.getLiteralLexicalForm();
        if (text.isEmpty()) {
            return new DggsValue(
                List.of(),
                DEFAULT_RESOLUTION,
                GEOMETRIES.createGeometryCollection()
            );
        }
        Matcher matcher = LITERAL.matcher(text);
        if (!matcher.matches() || !PROFILE.equals(matcher.group(1))) {
            throw new ExprEvalException("Invalid PULSE H3 DGGS literal");
        }
        List<String> cells = Arrays.stream(matcher.group(3).trim().split("[\\s,]+"))
            .filter(cell -> !cell.isBlank())
            .toList();
        if (cells.isEmpty()) {
            throw new ExprEvalException("H3 CELL(S) must contain an index");
        }
        if (matcher.group(2).equals("CELL") && cells.size() != 1) {
            throw new ExprEvalException("CELL requires exactly one H3 index");
        }
        int resolution = H3.getResolution(cells.get(0));
        for (String cell : cells) {
            if (!H3.isValidCell(cell) || H3.getResolution(cell) != resolution) {
                throw new ExprEvalException("Invalid or mixed-resolution H3 index");
            }
        }
        return new DggsValue(
            List.copyOf(new TreeSet<>(cells)),
            resolution,
            cellsGeometry(cells)
        );
    }

    private static Geometry cellsGeometry(List<String> cells) {
        List<Geometry> polygons = new ArrayList<>();
        for (String cell : cells) {
            List<LatLng> boundary = H3.cellToBoundary(cell);
            Coordinate[] coordinates = new Coordinate[boundary.size() + 1];
            for (int index = 0; index < boundary.size(); index++) {
                LatLng point = boundary.get(index);
                coordinates[index] = new Coordinate(point.lng, point.lat);
            }
            coordinates[boundary.size()] = coordinates[0].copy();
            polygons.add(GEOMETRIES.createPolygon(coordinates));
        }
        return UnaryUnionOp.union(polygons);
    }

    private static NodeValue dggs(Geometry geometry, int resolution) {
        List<String> cells = cover(geometry, resolution);
        String lexical;
        if (geometry.isEmpty() || cells.isEmpty()) {
            lexical = "";
        } else {
            lexical = "<" + PROFILE + "> "
                + (cells.size() == 1 ? "CELL" : "CELLS")
                + " (" + String.join(" ", cells) + ")";
        }
        return NodeValue.makeNode(
            NodeFactory.createLiteral(
                lexical,
                "",
                TypeMapper.getInstance().getSafeTypeByName(DGGS)
            )
        );
    }

    private static List<String> cover(Geometry geometry, int resolution) {
        if (geometry.isEmpty()) {
            return List.of();
        }
        Set<String> cells = new TreeSet<>();
        collectCells(geometry, resolution, cells);
        if (cells.isEmpty()) {
            Coordinate centre = geometry.getCentroid().getCoordinate();
            if (centre != null) {
                cells.add(H3.latLngToCellAddress(centre.y, centre.x, resolution));
            }
        }
        return List.copyOf(cells);
    }

    private static void collectCells(
        Geometry geometry,
        int resolution,
        Set<String> cells
    ) {
        if (geometry instanceof Polygon polygon) {
            List<LatLng> shell = latLngs(polygon.getExteriorRing());
            List<List<LatLng>> holes = new ArrayList<>();
            for (int index = 0; index < polygon.getNumInteriorRing(); index++) {
                holes.add(latLngs(polygon.getInteriorRingN(index)));
            }
            cells.addAll(H3.polygonToCellAddresses(shell, holes, resolution));
            return;
        }
        if (geometry instanceof Point point) {
            if (!point.isEmpty()) {
                cells.add(
                    H3.latLngToCellAddress(point.getY(), point.getX(), resolution)
                );
            }
            return;
        }
        if (geometry instanceof LineString line) {
            for (Coordinate coordinate : line.getCoordinates()) {
                cells.add(
                    H3.latLngToCellAddress(coordinate.y, coordinate.x, resolution)
                );
            }
            return;
        }
        for (int index = 0; index < geometry.getNumGeometries(); index++) {
            collectCells(geometry.getGeometryN(index), resolution, cells);
        }
    }

    private static List<LatLng> latLngs(LineString ring) {
        Coordinate[] coordinates = ring.getCoordinates();
        List<LatLng> points = new ArrayList<>(Math.max(0, coordinates.length - 1));
        for (int index = 0; index < coordinates.length - 1; index++) {
            points.add(new LatLng(coordinates[index].y, coordinates[index].x));
        }
        return points;
    }

    private static void requireResolution(DggsValue left, DggsValue right) {
        if (left.resolution() != right.resolution()) {
            throw new ExprEvalException("H3 operands must use the same resolution");
        }
    }

    private static Geometry metricGeometry(Geometry geometry) {
        return LocalFrame.forGeometry(geometry).project(geometry);
    }

    private static double metricLength(Geometry geometry) {
        return metricGeometry(geometry).getLength();
    }

    private static double metricPerimeter(Geometry geometry) {
        return metricGeometry(geometry).getBoundary().getLength();
    }

    private static double convertSquareMetres(double value, String unit) {
        return switch (unit) {
            case SQUARE_METRE -> value;
            case SQUARE_KILOMETRE -> value / 1_000_000.0;
            default -> throw new ExprEvalException("Unsupported area unit: " + unit);
        };
    }

    private record LocalFrame(
        double centreX,
        double centreY,
        double metresPerDegreeX,
        double metresPerDegreeY
    ) {
        private static LocalFrame forGeometry(Geometry geometry) {
            Point centre = geometry.isEmpty()
                ? GEOMETRIES.createPoint(new Coordinate(0.0, 0.0))
                : geometry.getCentroid();
            double latitude = centre.getY();
            return new LocalFrame(
                centre.getX(),
                latitude,
                111_320.0 * Math.max(1.0e-9, Math.cos(Math.toRadians(latitude))),
                110_574.0
            );
        }

        private Geometry project(Geometry source) {
            Geometry copy = source.copy();
            copy.apply((CoordinateFilter) coordinate -> {
                coordinate.x = (coordinate.x - centreX) * metresPerDegreeX;
                coordinate.y = (coordinate.y - centreY) * metresPerDegreeY;
            });
            copy.geometryChanged();
            return copy;
        }

        private Geometry unproject(Geometry source) {
            Geometry copy = source.copy();
            copy.apply((CoordinateFilter) coordinate -> {
                coordinate.x = coordinate.x / metresPerDegreeX + centreX;
                coordinate.y = coordinate.y / metresPerDegreeY + centreY;
            });
            copy.geometryChanged();
            return copy;
        }
    }

    private static NodeValue anyUri(String value) {
        return NodeValue.makeNode(
            NodeFactory.createLiteral(value, "", XSDDatatype.XSDanyURI)
        );
    }

    private static String lexical(NodeValue value) {
        Node node = value.asNode();
        if (node.isURI()) {
            return node.getURI();
        }
        if (node.isLiteral()) {
            return node.getLiteralLexicalForm();
        }
        throw new ExprEvalException("Expected IRI or xsd:anyURI literal");
    }

    private static ExprEvalException failure(Exception error) {
        return error instanceof ExprEvalException expression
            ? expression
            : new ExprEvalException(
                String.format(
                    Locale.ROOT,
                    "%s: %s",
                    error.getClass().getSimpleName(),
                    error.getMessage()
                )
            );
    }
}
