package dev.atof.eclipse;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.Set;

/** Plain Java transport; no redirects, no request or response logging. */
public final class LocalTransport {
    private final URI origin;
    private final HttpClient client;
    private static final int LIMIT = 8_000_000;

    public LocalTransport(String raw) {
        this.origin = validateOrigin(raw);
        this.client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(4))
                .followRedirects(HttpClient.Redirect.NEVER).build();
    }

    public static URI validateOrigin(String raw) {
        URI uri = URI.create(raw);
        if (!"http".equals(uri.getScheme()) || uri.getHost() == null ||
            !Set.of("127.0.0.1", "localhost", "[::1]").contains(uri.getHost()) ||
            uri.getRawUserInfo() != null || uri.getRawQuery() != null || uri.getRawFragment() != null ||
            !(uri.getRawPath().isEmpty() || "/".equals(uri.getRawPath())) ||
            uri.getPort() < 1 || uri.getPort() > 65535)
            throw new IllegalArgumentException("Use a loopback HTTP origin with a port");
        return URI.create("http://" + uri.getRawAuthority());
    }

    public URI dashboard() { return origin.resolve("/dashboard"); }

    public String request(String route, String method, String body, Map<String,String> headers) throws IOException, InterruptedException {
        if (!route.startsWith("/v1/") || route.contains("..") || route.contains("\\") || route.contains("?") || route.contains("#"))
            throw new IllegalArgumentException("Invalid local route");
        URI target = origin.resolve(route);
        HttpRequest.Builder b = HttpRequest.newBuilder(target).timeout(Duration.ofSeconds(15));
        headers.forEach(b::header);
        if (body == null) b.method(method, HttpRequest.BodyPublishers.noBody());
        else b.header("Content-Type", "application/json").method(method, HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8));
        HttpResponse<InputStream> response = client.send(b.build(), HttpResponse.BodyHandlers.ofInputStream());
        try (InputStream stream = response.body()) {
            if (response.statusCode() != 200) throw new IOException("Local service HTTP " + response.statusCode());
            byte[] bytes = stream.readNBytes(LIMIT + 1);
            if (bytes.length > LIMIT) throw new IOException("Local response too large");
            return new String(bytes, StandardCharsets.UTF_8);
        }
    }
}
