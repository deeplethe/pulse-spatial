package org.pulsebench;

import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

import org.apache.jena.geosparql.configuration.GeoSPARQLConfig;
import org.apache.jena.geosparql.configuration.GeoSPARQLOperations;
import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.ResultSet;
import org.apache.jena.query.ResultSetFactory;
import org.apache.jena.query.ResultSetFormatter;
import org.apache.jena.query.ResultSetRewindable;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.RDFDataMgr;

/**
 * Minimal, separately implemented Apache Jena GeoSPARQL query harness.
 *
 * <p>The harness deliberately contains no PULSE geometry code. It loads a
 * projected Turtle graph, evaluates standard GeoSPARQL filter functions, and
 * writes standard SPARQL Results JSON to stdout.</p>
 */
public final class GeoSparqlHarness {
    private static final String[] QUERY_REWRITE_RELATIONS = {
        "sfEquals", "sfDisjoint", "sfIntersects", "sfTouches",
        "sfCrosses", "sfWithin", "sfContains", "sfOverlaps",
        "ehEquals", "ehDisjoint", "ehMeet", "ehOverlap",
        "ehCovers", "ehCoveredBy", "ehInside", "ehContains",
        "rcc8eq", "rcc8dc", "rcc8ec", "rcc8po",
        "rcc8tppi", "rcc8tpp", "rcc8ntpp", "rcc8ntppi"
    };

    private static final String QUERY = """
        PREFIX geo:  <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        SELECT ?subject ?region
               (geof:sfWithin(?subjectWkt, ?regionWkt) AS ?inside)
               (geof:sfIntersects(?subjectWkt, ?regionWkt) AS ?coveredBy)
               (geof:sfDisjoint(?subjectWkt, ?regionWkt) AS ?disjoint)
               (geof:sfTouches(?subjectWkt, ?regionWkt) AS ?onBoundary)
        WHERE {
          ?subject a geo:Feature ;
                   geo:hasGeometry/geo:asWKT ?subjectWkt .
          ?region  a geo:Feature ;
                   geo:hasGeometry/geo:asWKT ?regionWkt .
          FILTER(CONTAINS(STR(?subject), "/instance/"))
          FILTER(CONTAINS(STR(?region), "/region/"))
        }
        ORDER BY ?subject ?region
        """;

    private GeoSparqlHarness() {}

    public static void main(String[] args) throws Exception {
        if (
            args.length == 4
                && args[0].equals("--query-rewrite")
                && args[1].equals("--query")
        ) {
            runQuery(Path.of(args[2]), Path.of(args[3]), true, false, false);
            return;
        }
        if (
            args.length == 4
                && args[0].equals("--geometry-profile")
                && args[1].equals("--query")
        ) {
            runQuery(Path.of(args[2]), Path.of(args[3]), false, true, false);
            return;
        }
        if (
            args.length == 4
                && args[0].equals("--dggs-profile")
                && args[1].equals("--query")
        ) {
            runQuery(Path.of(args[2]), Path.of(args[3]), false, false, true);
            return;
        }
        if (args.length == 3 && args[0].equals("--query")) {
            runQuery(Path.of(args[1]), Path.of(args[2]), false, false, false);
            return;
        }
        if (args.length != 1) {
            System.err.println(
                "usage: harness <projected-data.ttl> | "
                    + "--query <data.ttl> <probe.rq> | "
                    + "--query-rewrite --query <data.ttl> <probe.rq> | "
                    + "--geometry-profile --query <data.ttl> <probe.rq> | "
                    + "--dggs-profile --query <data.ttl> <probe.rq>"
            );
            System.exit(2);
        }
        Path data = Path.of(args[0]).toAbsolutePath().normalize();
        if (!Files.isRegularFile(data)) {
            System.err.println("input does not exist: " + data);
            System.exit(2);
        }

        long initializationStart = System.nanoTime();
        GeoSPARQLConfig.setupMemoryIndex();
        long loadStart = System.nanoTime();
        Model model = RDFDataMgr.loadModel(data.toUri().toString());
        long queryStart = System.nanoTime();
        try (QueryExecution execution = QueryExecution.create(QUERY, model)) {
            ResultSet results = execution.execSelect();
            ResultSetRewindable materialized = ResultSetFactory.copyResults(results);
            long queryEnd = System.nanoTime();
            OutputStream output = System.out;
            ResultSetFormatter.outputAsJSON(output, materialized);
            System.err.printf(
                Locale.ROOT,
                "PULSE_JENA_TIMING {\"initializationSeconds\":%.9f,"
                    + "\"loadSeconds\":%.9f,\"querySeconds\":%.9f,"
                    + "\"rows\":%d}%n",
                (loadStart - initializationStart) / 1_000_000_000.0,
                (queryStart - loadStart) / 1_000_000_000.0,
                (queryEnd - queryStart) / 1_000_000_000.0,
                materialized.size()
            );
        } finally {
            model.close();
            GeoSPARQLConfig.reset();
        }
    }

    private static void runQuery(
        Path dataPath,
        Path queryPath,
        boolean queryRewrite,
        boolean geometryProfile,
        boolean dggsProfile
    ) throws Exception {
        Path data = dataPath.toAbsolutePath().normalize();
        Path queryFile = queryPath.toAbsolutePath().normalize();
        if (!Files.isRegularFile(data) || !Files.isRegularFile(queryFile)) {
            System.err.println("query input does not exist");
            System.exit(2);
        }
        GeoSPARQLConfig.setupMemoryIndex();
        Model model = RDFDataMgr.loadModel(data.toUri().toString());
        if (queryRewrite) {
            applyWktQueryRewrite(model);
        } else {
            GeoSPARQLOperations.applyInferencing(model);
        }
        if (geometryProfile) {
            PulseGeoSparql11.registerGeometryProfile();
        }
        if (dggsProfile) {
            PulseH3Dggs.registerProfile();
        }
        Query query = QueryFactory.read(queryFile.toUri().toString());
        try (QueryExecution execution = QueryExecution.create(query, model)) {
            if (query.isAskType()) {
                System.out.printf(
                    Locale.ROOT,
                    "{\"boolean\":%s}%n",
                    execution.execAsk() ? "true" : "false"
                );
            } else if (query.isSelectType()) {
                ResultSetRewindable results = ResultSetFactory.copyResults(
                    execution.execSelect()
                );
                ResultSetFormatter.outputAsJSON(System.out, results);
            } else {
                System.err.println("only ASK and SELECT probes are supported");
                System.exit(2);
            }
        } finally {
            model.close();
            GeoSPARQLConfig.reset();
        }
    }

    /**
     * Materialize the GeoSPARQL 1.1 query-rewrite rules for the WKT profile.
     *
     * <p>The four rule shapes in Clause 13 are covered by resolving each
     * spatial object through either geo:hasDefaultGeometry/geo:asWKT or a
     * direct geo:asWKT serialization. The resulting relation triples make
     * ordinary basic graph patterns observe the same relation as the
     * corresponding GeoSPARQL function.</p>
     */
    private static void applyWktQueryRewrite(Model model) {
        Model additions = ModelFactory.createDefaultModel();
        for (String relation : QUERY_REWRITE_RELATIONS) {
            String construct = """
                PREFIX geo:  <http://www.opengis.net/ont/geosparql#>
                PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
                CONSTRUCT {
                  ?left geo:%1$s ?right .
                }
                WHERE {
                  {
                    ?left geo:hasDefaultGeometry/geo:asWKT ?leftLiteral .
                  } UNION {
                    ?left geo:asWKT ?leftLiteral .
                  }
                  {
                    ?right geo:hasDefaultGeometry/geo:asWKT ?rightLiteral .
                  } UNION {
                    ?right geo:asWKT ?rightLiteral .
                  }
                  FILTER(geof:%1$s(?leftLiteral, ?rightLiteral))
                }
                """.formatted(relation);
            try (
                QueryExecution execution = QueryExecution.create(
                    QueryFactory.create(construct),
                    model
                )
            ) {
                execution.execConstruct(additions);
            }
        }
        model.add(additions);
        additions.close();
    }
}
