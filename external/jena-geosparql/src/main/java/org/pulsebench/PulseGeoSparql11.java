package org.pulsebench;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.apache.jena.datatypes.TypeMapper;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.geosparql.implementation.GeometryWrapper;
import org.apache.jena.geosparql.implementation.GeometryWrapperFactory;
import org.apache.jena.geosparql.implementation.UnitsOfMeasure;
import org.apache.jena.geosparql.implementation.datatype.GMLDatatype;
import org.apache.jena.geosparql.implementation.datatype.WKTDatatype;
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
import org.locationtech.jts.geom.LineString;
import org.locationtech.jts.geom.MultiLineString;
import org.locationtech.jts.geom.MultiPoint;
import org.locationtech.jts.geom.MultiPolygon;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.operation.union.UnaryUnionOp;

/** PULSE implementations of GeoSPARQL 1.1 functions absent from Jena 6.1.0. */
public final class PulseGeoSparql11 {
    private static final String GEOF =
        "http://www.opengis.net/def/function/geosparql/";
    private static final String KML =
        "http://www.opengis.net/ont/geosparql#kmlLiteral";
    private static final String SF = "http://www.opengis.net/ont/sf#";
    private static final double DEFAULT_CONCAVE_HULL_RATIO = 0.5;

    private PulseGeoSparql11() {}

    public static void registerGeometryProfile() {
        FunctionRegistry functions = FunctionRegistry.get();
        registerUnary(functions, "boundingCircle", UnaryMode.BOUNDING_CIRCLE);
        registerUnary(functions, "centroid", UnaryMode.CENTROID);
        registerUnary(functions, "concaveHull", UnaryMode.CONCAVE_HULL);
        registerUnary(functions, "geometryType", UnaryMode.GEOMETRY_TYPE);
        registerUnary(functions, "is3D", UnaryMode.IS_3D);
        registerUnary(functions, "isEmpty", UnaryMode.IS_EMPTY);
        registerUnary(functions, "isMeasured", UnaryMode.IS_MEASURED);
        registerUnary(functions, "getSRID", UnaryMode.GET_SRID);
        registerUnary(functions, "asWKT", UnaryMode.AS_WKT);
        registerUnary(functions, "asKML", UnaryMode.AS_KML);
        functions.put(GEOF + "metricBuffer", uri -> new MetricBuffer());
        functions.put(GEOF + "metricDistance", uri -> new MetricDistance());
        functions.put(GEOF + "buffer", uri -> new Buffer());
        functions.put(GEOF + "distance", uri -> new Distance());
        functions.put(GEOF + "transform", uri -> new Transform());
        functions.put(GEOF + "asGML", uri -> new AsGml());
        functions.put(GEOF + "sfEquals", uri -> new SfEquals());

        registerAggregate("aggBoundingBox", AggregateMode.BOUNDING_BOX);
        registerAggregate("aggBoundingCircle", AggregateMode.BOUNDING_CIRCLE);
        registerAggregate("aggCentroid", AggregateMode.CENTROID);
        registerAggregate("aggConcaveHull", AggregateMode.CONCAVE_HULL);
        registerAggregate("aggConvexHull", AggregateMode.CONVEX_HULL);
        registerAggregate("aggUnion", AggregateMode.UNION);
    }

    private static void registerUnary(
        FunctionRegistry registry,
        String localName,
        UnaryMode mode
    ) {
        registry.put(GEOF + localName, uri -> new UnaryGeometryFunction(mode));
    }

    private static void registerAggregate(String localName, AggregateMode mode) {
        AggregateRegistry.register(
            GEOF + localName,
            (aggregate, distinct) -> new SpatialAccumulator(
                aggregate,
                distinct,
                mode
            )
        );
    }

    private static GeometryWrapper geometry(NodeValue value) {
        return GeometryWrapper.extract(value);
    }

    private static NodeValue geometryValue(
        Geometry geometry,
        GeometryWrapper source
    ) {
        return GeometryWrapperFactory.createGeometry(
            geometry,
            source.getSrsURI(),
            WKTDatatype.URI
        ).asNodeValue();
    }

    private static NodeValue geometryValue(
        GeometryWrapper geometry,
        String datatype
    ) {
        return NodeValue.makeNode(geometry.asLiteral(datatype).asNode());
    }

    private static NodeValue anyUri(String value) {
        return NodeValue.makeNode(
            NodeFactory.createLiteral(value, "", XSDDatatype.XSDanyURI)
        );
    }

    private static String lexical(NodeValue value) {
        Node node = value.asNode();
        if (node.isLiteral()) {
            return node.getLiteralLexicalForm();
        }
        if (node.isURI()) {
            return node.getURI();
        }
        throw new ExprEvalException("Expected an IRI or xsd:anyURI literal");
    }

    private static ExprEvalException failure(Exception error) {
        return new ExprEvalException(error.getMessage());
    }

    private enum UnaryMode {
        BOUNDING_CIRCLE,
        CENTROID,
        CONCAVE_HULL,
        GEOMETRY_TYPE,
        IS_3D,
        IS_EMPTY,
        IS_MEASURED,
        GET_SRID,
        AS_WKT,
        AS_KML
    }

    private static final class UnaryGeometryFunction extends FunctionBase1 {
        private final UnaryMode mode;

        private UnaryGeometryFunction(UnaryMode mode) {
            this.mode = mode;
        }

        @Override
        public NodeValue exec(NodeValue value) {
            if (mode == UnaryMode.IS_EMPTY) {
                Node node = value.asNode();
                if (node.isLiteral() && node.getLiteralLexicalForm().isEmpty()) {
                    return NodeValue.TRUE;
                }
            }
            try {
                GeometryWrapper wrapper = geometry(value);
                Geometry jts = wrapper.getXYGeometry();
                return switch (mode) {
                    case BOUNDING_CIRCLE -> geometryValue(
                        new MinimumBoundingCircle(jts).getCircle(),
                        wrapper
                    );
                    case CENTROID -> geometryValue(jts.getCentroid(), wrapper);
                    case CONCAVE_HULL -> geometryValue(
                        ConcaveHull.concaveHullByLengthRatio(
                            jts,
                            DEFAULT_CONCAVE_HULL_RATIO
                        ),
                        wrapper
                    );
                    case GEOMETRY_TYPE -> anyUri(
                        SF + wrapper.getGeometryType()
                    );
                    case IS_3D -> NodeValue.makeBoolean(
                        wrapper.getSpatialDimension() == 3
                    );
                    case IS_EMPTY -> NodeValue.makeBoolean(wrapper.isEmpty());
                    case IS_MEASURED -> NodeValue.makeBoolean(isMeasured(jts));
                    case GET_SRID -> anyUri(wrapper.getSRID());
                    case AS_WKT -> geometryValue(wrapper, WKTDatatype.URI);
                    case AS_KML -> NodeValue.makeNode(
                        NodeFactory.createLiteral(
                            kml(jts),
                            "",
                            TypeMapper.getInstance().getSafeTypeByName(KML)
                        )
                    );
                };
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private static final class MetricBuffer extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue value, NodeValue radius) {
            return buffered(value, radius.getDouble(), Unit_URI.METRE_URL);
        }
    }

    private static final class Buffer extends FunctionBase3 {
        @Override
        public NodeValue exec(
            NodeValue value,
            NodeValue radius,
            NodeValue units
        ) {
            return buffered(value, radius.getDouble(), lexical(units));
        }
    }

    private static NodeValue buffered(
        NodeValue value,
        double radius,
        String units
    ) {
        try {
            GeometryWrapper source = geometry(value);
            if (!source.getSrsInfo().isGeographic()) {
                return geometryValue(
                    source.buffer(radius, units),
                    WKTDatatype.URI
                );
            }
            double metres = UnitsOfMeasure.conversion(
                radius,
                units,
                Unit_URI.METRE_URL
            );
            Geometry local = source.getXYGeometry().copy();
            Point centre = local.getCentroid();
            double centreX = centre.getX();
            double centreY = centre.getY();
            double radians = Math.toRadians(centreY);
            double metresPerDegreeX = 111_320.0 * Math.cos(radians);
            double metresPerDegreeY = 110_574.0;
            local.apply((CoordinateFilter) coordinate -> {
                coordinate.x = (coordinate.x - centreX) * metresPerDegreeX;
                coordinate.y = (coordinate.y - centreY) * metresPerDegreeY;
            });
            local.geometryChanged();
            Geometry result = local.buffer(metres);
            result.apply((CoordinateFilter) coordinate -> {
                coordinate.x = coordinate.x / metresPerDegreeX + centreX;
                coordinate.y = coordinate.y / metresPerDegreeY + centreY;
            });
            result.geometryChanged();
            return geometryValue(result, source);
        } catch (Exception error) {
            throw failure(error);
        }
    }

    private static final class MetricDistance extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue left, NodeValue right) {
            try {
                return NodeValue.makeDouble(
                    geometry(left).distance(geometry(right))
                );
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private static final class Distance extends FunctionBase3 {
        @Override
        public NodeValue exec(
            NodeValue left,
            NodeValue right,
            NodeValue units
        ) {
            try {
                return NodeValue.makeDouble(
                    geometry(left).distance(geometry(right), lexical(units))
                );
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private static final class Transform extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue value, NodeValue targetSrs) {
            try {
                return geometryValue(
                    geometry(value).transform(lexical(targetSrs)),
                    WKTDatatype.URI
                );
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private static final class AsGml extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue value, NodeValue profile) {
            String requested = lexical(profile);
            if (!requested.equals("GML 3.2.1")) {
                throw new ExprEvalException(
                    "Supported GML profile is GML 3.2.1"
                );
            }
            try {
                return geometryValue(geometry(value), GMLDatatype.URI);
            } catch (Exception error) {
                throw failure(error);
            }
        }
    }

    private static final class SfEquals extends FunctionBase2 {
        @Override
        public NodeValue exec(NodeValue left, NodeValue right) {
            try {
                return NodeValue.makeBoolean(
                    geometry(left).equalsTopo(geometry(right))
                );
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

    private static final class SpatialAccumulator implements Accumulator {
        private final List<Expr> arguments;
        private final boolean distinct;
        private final AggregateMode mode;
        private final List<Geometry> geometries = new ArrayList<>();
        private final Set<Node> seen = new HashSet<>();
        private GeometryWrapper source;
        private double targetRatio = DEFAULT_CONCAVE_HULL_RATIO;

        private SpatialAccumulator(
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
                GeometryWrapper wrapper = geometry(value);
                if (source == null) {
                    source = wrapper;
                } else {
                    wrapper = source.checkTransformSRS(wrapper);
                }
                geometries.add(wrapper.getXYGeometry());
                if (arguments.size() > 1) {
                    targetRatio = arguments
                        .get(1)
                        .eval(binding, environment)
                        .getDouble();
                }
            } catch (ExprEvalException error) {
                // SPARQL aggregates ignore expression errors and unbound rows.
            } catch (Exception error) {
                throw failure(error);
            }
        }

        @Override
        public NodeValue getValue() {
            if (source == null || geometries.isEmpty()) {
                return null;
            }
            Geometry union = UnaryUnionOp.union(geometries);
            Geometry result = switch (mode) {
                case BOUNDING_BOX -> union.getFactory().toGeometry(
                    union.getEnvelopeInternal()
                );
                case BOUNDING_CIRCLE -> new MinimumBoundingCircle(
                    union
                ).getCircle();
                case CENTROID -> union.getCentroid();
                case CONCAVE_HULL -> ConcaveHull.concaveHullByLengthRatio(
                    union,
                    targetRatio
                );
                case CONVEX_HULL -> union.convexHull();
                case UNION -> union;
            };
            return geometryValue(result, source);
        }
    }

    private static boolean isMeasured(Geometry geometry) {
        for (Coordinate coordinate : geometry.getCoordinates()) {
            if (!Double.isNaN(coordinate.getM())) {
                return true;
            }
        }
        return false;
    }

    private static String kml(Geometry geometry) {
        String body;
        if (geometry instanceof Point point) {
            body = "<Point><coordinates>" + coordinate(point.getCoordinate())
                + "</coordinates></Point>";
        } else if (geometry instanceof LineString line) {
            body = "<LineString><coordinates>" + coordinates(line)
                + "</coordinates></LineString>";
        } else if (geometry instanceof Polygon polygon) {
            StringBuilder polygonXml = new StringBuilder("<Polygon>");
            polygonXml.append("<outerBoundaryIs><LinearRing><coordinates>")
                .append(coordinates(polygon.getExteriorRing()))
                .append("</coordinates></LinearRing></outerBoundaryIs>");
            for (int index = 0; index < polygon.getNumInteriorRing(); index++) {
                polygonXml.append(
                    "<innerBoundaryIs><LinearRing><coordinates>"
                ).append(coordinates(polygon.getInteriorRingN(index)))
                    .append("</coordinates></LinearRing></innerBoundaryIs>");
            }
            body = polygonXml.append("</Polygon>").toString();
        } else if (
            geometry instanceof GeometryCollection
                || geometry instanceof MultiPoint
                || geometry instanceof MultiLineString
                || geometry instanceof MultiPolygon
        ) {
            StringBuilder collection = new StringBuilder("<MultiGeometry>");
            for (int index = 0; index < geometry.getNumGeometries(); index++) {
                collection.append(kmlBody(geometry.getGeometryN(index)));
            }
            body = collection.append("</MultiGeometry>").toString();
        } else {
            throw new ExprEvalException(
                "Unsupported KML geometry type: " + geometry.getGeometryType()
            );
        }
        return body.replaceFirst(">", " xmlns=\"http://www.opengis.net/kml/2.2\">");
    }

    private static String kmlBody(Geometry geometry) {
        return kml(geometry).replaceFirst(
            " xmlns=\"http://www.opengis.net/kml/2.2\"",
            ""
        );
    }

    private static String coordinates(LineString line) {
        StringBuilder value = new StringBuilder();
        for (Coordinate coordinate : line.getCoordinates()) {
            if (!value.isEmpty()) {
                value.append(' ');
            }
            value.append(coordinate(coordinate));
        }
        return value.toString();
    }

    private static String coordinate(Coordinate coordinate) {
        String value = coordinate.getX() + "," + coordinate.getY();
        return Double.isNaN(coordinate.getZ())
            ? value
            : value + "," + coordinate.getZ();
    }
}
