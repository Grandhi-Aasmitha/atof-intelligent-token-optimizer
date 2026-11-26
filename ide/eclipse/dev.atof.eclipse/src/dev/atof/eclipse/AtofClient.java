package dev.atof.eclipse;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.util.Map;
import java.net.URI;

/** The same loopback service used by VS Code; no separate optimizer. */
final class AtofClient {
    private final LocalTransport transport;
    AtofClient() { this(new LocalTransport(System.getProperty("atof.apiUrl", "http://127.0.0.1:8081"))); }
    AtofClient(LocalTransport transport) { this.transport=transport; }
    URI dashboard() { return transport.dashboard(); }
    private JsonObject call(String route, String method, JsonObject body, Map<String,String> headers) throws Exception {
        return JsonParser.parseString(transport.request(route,method,body==null?null:body.toString(),headers)).getAsJsonObject();
    }
    JsonObject control() throws Exception { return call("/v1/control","GET",null,Map.of()); }
    JsonObject enabled(boolean enabled) throws Exception {
        JsonObject body=new JsonObject();body.addProperty("enabled",enabled);
        return call("/v1/control/enabled","PUT",body,Map.of("X-ATOF-Control","1"));
    }
    static JsonObject payload(String task,String text) {
        Evidence.validate(task,text);
        JsonObject body=new JsonObject();body.addProperty("task",task);
        if(!text.isEmpty())body.addProperty(Evidence.slot(text),text);
        return body;
    }
    JsonObject candidate(String task,String text) throws Exception {
        return call("/v1/optimize","POST",payload(task,text),Map.of());
    }
    String prepare(String adapter,String task,String text) throws Exception {
        if(!adapter.equals("eclipse_openai")&&!adapter.equals("eclipse_gemini"))
            throw new IllegalArgumentException("Unsupported adapter");
        JsonObject result=call("/v1/adapters/"+adapter+"/prepare","POST",payload(task,text),Map.of("X-ATOF-Adapter","1"));
        return accept(result,adapter,task,text);
    }
    static String accept(JsonObject r,String adapter,String task,String original) {
        String agent=adapter.equals("eclipse_openai")?"chatgpt":"gemini";
        JsonObject report=r.getAsJsonObject("report");
        String prompt=r.get("prompt").getAsString();
        JsonObject content=JsonParser.parseString(prompt).getAsJsonObject();
        if(!adapter.equals(r.get("adapter_id").getAsString()) || !agent.equals(report.get("agent").getAsString()) ||
           !"owned_payload_prepared".equals(report.get("delivery_status").getAsString()) ||
           content.size()!=2 || !content.get("task").isJsonPrimitive() || !content.getAsJsonPrimitive("task").isString() ||
           !content.get("evidence").isJsonPrimitive() || !content.getAsJsonPrimitive("evidence").isString() ||
           !task.equals(content.get("task").getAsString()))
            throw new IllegalArgumentException("Unexpected input framing");
        String evidence=content.get("evidence").getAsString();
        long before=r.get("original_prompt_estimate").getAsBigDecimal().longValueExact();
        long after=r.get("prepared_prompt_estimate").getAsBigDecimal().longValueExact();
        if(before<0||after<0||after>before||r.get("prompt_estimated_reduction").getAsBigDecimal().longValueExact()!=before-after)
            throw new IllegalArgumentException("Invalid estimates");
        if(!original.equals(evidence) && (after>=before || !"enabled".equals(report.get("control_policy").getAsString()) ||
            !"passed".equals(report.get("fidelity_status").getAsString()) || report.getAsJsonArray("executed_features").isEmpty()))
            throw new IllegalArgumentException("Unverified reduction");
        if(original.equals(evidence)&&after!=before)throw new IllegalArgumentException("Inconsistent estimates");
        return prompt;
    }
}
