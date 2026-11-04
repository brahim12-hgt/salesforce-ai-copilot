/**
 * Appels HTTP vers le backend FastAPI via Named Credential (clé API jamais exposée au navigateur).
 */
public with sharing class CopilotClient {
    private static final String BASE = 'callout:AI_Copilot';

    public static String post(String path, Object body) {
        return send('POST', path, body == null ? '{}' : JSON.serialize(body));
    }

    public static String get(String path) {
        return send('GET', path, null);
    }

    private static String send(String method, String path, String payload) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(BASE + path);
        req.setMethod(method);
        req.setTimeout(60000);
        req.setHeader('Content-Type', 'application/json');
        req.setHeader('X-API-Key', '{!$Credential.Password}');
        if (payload != null) {
            req.setBody(payload);
        }
        HttpResponse res = new Http().send(req);
        if (res.getStatusCode() >= 400) {
            throw new CalloutException('Backend IA indisponible (' + res.getStatusCode() + ').');
        }
        return res.getBody();
    }
}
