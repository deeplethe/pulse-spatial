package org.pulsebench;

import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

import org.apache.jena.geosparql.configuration.GeoSPARQLConfig;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.query.ResultSetFactory;
import org.apache.jena.query.ResultSetFormatter;
import org.apache.jena.query.ResultSetRewindable;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.RDFDataMgr;

/**
 * Minimal, separately implemented Apache Jena GeoSPARQL query harness.
 *
 * <p>The harness deliberately contains no PULSE geometry code. It loads a
 * projected Turtle graph, evaluates standard GeoSPARQL filter functions, and
 * writes standard SPARQL Results JSON to stdout.</p>
 */
public final class GeoSparqlHarness {
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
        if (args.length != 1) {
            System.err.println("usage: harness <projected-data.ttl>");
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
}
