package dev.atof.eclipse;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

/** Explicit single-turn provider requests only. No native assistant access or retry loop. */
final class ProviderSender {
    enum Provider {
        OPENAI("OpenAI API","OPENAI_API_KEY","eclipse_openai"),
        GEMINI("Gemini API","GEMINI_API_KEY","eclipse_gemini");
        final String label,key,adapter;
        Provider(String label,String key,String adapter){this.label=label;this.key=key;this.adapter=adapter;}
    }
    static void validateModel(String model) {
        if(model==null||!model.matches("[A-Za-z0-9_.-]{1,100}"))
            throw new IllegalArgumentException("Invalid model ID");
    }
    static JsonObject body(Provider provider,String model,String prompt){
        validateModel(model);
        JsonObject b=new JsonObject();
        if(provider==Provider.OPENAI){
            b.addProperty("model",model);b.addProperty("input",prompt);b.addProperty("store",false);
            b.addProperty("max_output_tokens",2048);
        }else{
            JsonObject part=new JsonObject();part.addProperty("text",prompt);
            JsonArray parts=new JsonArray();parts.add(part);
            JsonObject msg=new JsonObject();msg.addProperty("role","user");msg.add("parts",parts);
            JsonArray contents=new JsonArray();contents.add(msg);b.add("contents",contents);
            JsonObject generation=new JsonObject();generation.addProperty("maxOutputTokens",2048);b.add("generationConfig",generation);
        }
        return b;
    }
    static URI endpoint(Provider provider,String model) {
        validateModel(model);
        return URI.create(provider==Provider.OPENAI?"https://api.openai.com/v1/responses":
            "https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent");
    }
    static String send(Provider provider,String model,String prompt,String key) throws Exception {
        if(key==null||key.isBlank())throw new IllegalArgumentException("Approved provider credential unavailable");
        HttpRequest.Builder builder=HttpRequest.newBuilder(endpoint(provider,model)).timeout(Duration.ofSeconds(90))
            .header("Content-Type","application/json");
        if(provider==Provider.OPENAI)builder.header("Authorization","Bearer "+key);
        else builder.header("x-goog-api-key",key);
        HttpRequest req=builder.POST(HttpRequest.BodyPublishers.ofString(body(provider,model,prompt).toString(),StandardCharsets.UTF_8)).build();
        HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).followRedirects(HttpClient.Redirect.NEVER).build();
        HttpResponse<InputStream> response=client.send(req,HttpResponse.BodyHandlers.ofInputStream());
        try(InputStream stream=response.body()){
            if(response.statusCode()!=200)throw new IOException("Provider HTTP "+response.statusCode());
            byte[] bytes=stream.readNBytes(4_000_001);
            if(bytes.length>4_000_000)throw new IOException("Provider response too large");
            return parse(provider,JsonParser.parseString(new String(bytes,StandardCharsets.UTF_8)).getAsJsonObject());
        }
    }
    static String parse(Provider provider,JsonObject result) throws IOException {
        StringBuilder out=new StringBuilder();
        if(provider==Provider.OPENAI){
            if(!"completed".equals(result.get("status").getAsString()))throw new IOException("Incomplete model response");
            for(JsonElement item:result.getAsJsonArray("output")){
                JsonObject o=item.getAsJsonObject();
                if(!"message".equals(o.get("type").getAsString()))continue;
                for(JsonElement part:o.getAsJsonArray("content")){
                    JsonObject p=part.getAsJsonObject();
                    if("output_text".equals(p.get("type").getAsString()))out.append(p.get("text").getAsString());
                }
            }
        }else{
            JsonArray candidates=result.getAsJsonArray("candidates");
            if(candidates==null||candidates.isEmpty())throw new IOException("No model candidate");
            JsonObject c=candidates.get(0).getAsJsonObject();
            if(!"STOP".equals(c.get("finishReason").getAsString()))throw new IOException("Incomplete model response");
            for(JsonElement part:c.getAsJsonObject("content").getAsJsonArray("parts")){
                JsonObject p=part.getAsJsonObject();
                if(p.has("text")&&(!p.has("thought")||!p.get("thought").getAsBoolean()))out.append(p.get("text").getAsString());
            }
        }
        if(out.isEmpty())throw new IOException("No text response");
        return out.toString();
    }
}
