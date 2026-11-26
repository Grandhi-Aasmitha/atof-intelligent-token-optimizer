package dev.atof;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ProtocolTest {
    @Test void slots(){
        assertEquals("error_output",Evidence.slot("heartbeat\nRuntimeError: bad"));
        assertEquals("test_output",Evidence.slot("test_a PASSED\ntest_b FAILED"));
        assertEquals("diff",Evidence.slot("diff --git a/a b/a\n@@ -1 +1 @@\n-a\n+b"));
        assertEquals("context",Evidence.slot("regular text"));
        assertThrows(IllegalArgumentException.class,()->Evidence.validate("","x"));
    }
    @Test void origins(){
        assertEquals("http://127.0.0.1:8081",LocalTransport.validateOrigin("http://127.0.0.1:8081/").toString());
        for(String s:new String[]{"http://example.com:8081","https://localhost:8081","http://user@localhost:8081","http://localhost:8081/path","http://localhost:8081/?x=1"})
            assertThrows(IllegalArgumentException.class,()->LocalTransport.validateOrigin(s));
    }
    @Test void oneProviderInput(){
        String prompt="{\"task\":\"test\",\"evidence\":\"reduced\"}";
        JsonObject o=ProviderSender.body(ProviderSender.Provider.OPENAI,"approved-model",prompt);
        assertEquals(prompt,o.get("input").getAsString());assertFalse(o.get("store").getAsBoolean());
        JsonObject g=ProviderSender.body(ProviderSender.Provider.GEMINI,"approved-model",prompt);
        assertEquals(1,g.getAsJsonArray("contents").size());
        assertEquals(prompt,g.getAsJsonArray("contents").get(0).getAsJsonObject().getAsJsonArray("parts").get(0).getAsJsonObject().get("text").getAsString());
        assertThrows(IllegalArgumentException.class,()->ProviderSender.endpoint(ProviderSender.Provider.GEMINI,"../bad"));
    }
    @Test void originalOffAndReducedOn(){
        String response="{\"adapter_id\":\"jetbrains_openai\",\"prompt\":\"{\\\"task\\\":\\\"test\\\",\\\"evidence\\\":\\\"raw\\\"}\",\"original_prompt_estimate\":50,\"prepared_prompt_estimate\":50,\"prompt_estimated_reduction\":0,\"report\":{\"agent\":\"chatgpt\",\"delivery_status\":\"owned_payload_prepared\",\"control_policy\":\"disabled\",\"fidelity_status\":\"passed\",\"executed_features\":[]}}";
        JsonObject r=JsonParser.parseString(response).getAsJsonObject();
        assertEquals("{\"task\":\"test\",\"evidence\":\"raw\"}",AtofClient.accept(r,"jetbrains_openai","test","raw"));
        r.addProperty("prompt","{\"task\":\"test\",\"evidence\":\"changed\"}");
        assertThrows(IllegalArgumentException.class,()->AtofClient.accept(r,"jetbrains_openai","test","raw"));
        r.addProperty("prepared_prompt_estimate",20);r.addProperty("prompt_estimated_reduction",30);
        r.getAsJsonObject("report").addProperty("control_policy","enabled");
        r.getAsJsonObject("report").getAsJsonArray("executed_features").add("core.context");
        assertEquals("{\"task\":\"test\",\"evidence\":\"changed\"}",AtofClient.accept(r,"jetbrains_openai","test","raw"));
        assertThrows(IllegalArgumentException.class,()->AtofClient.accept(r,"jetbrains_openai","wrong","raw"));
    }
}
