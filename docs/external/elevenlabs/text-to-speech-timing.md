> This is a page from the ElevenLabs documentation. For a complete page index, fetch https://elevenlabs.io/docs/llms.txt. For the full documentation in a single file, fetch https://elevenlabs.io/docs/llms-full.txt.

# Create speech with timing

POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps
Content-Type: application/json

Generate speech from text with precise character-level timing information for audio-text synchronization.

Reference: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps

## OpenAPI Specification

```yaml
openapi: 3.1.0
info:
  title: api
  version: 1.0.0
paths:
  /v1/text-to-speech/{voice_id}/with-timestamps:
    post:
      operationId: convert-with-timestamps
      summary: Create speech with timing
      description: >-
        Generate speech from text with precise character-level timing
        information for audio-text synchronization.
      tags:
        - subpackage_textToSpeech
      parameters:
        - name: voice_id
          in: path
          description: >-
            Voice ID to be used, you can use https://api.elevenlabs.io/v1/voices
            to list all the available voices.
          required: true
          schema:
            type: string
        - name: enable_logging
          in: query
          description: >-
            When enable_logging is set to false zero retention mode will be used
            for the request. This will mean history features are unavailable for
            this request, including request stitching. Zero retention mode may
            only be used by enterprise customers.
          required: false
          schema:
            type: boolean
            default: true
        - name: optimize_streaming_latency
          in: query
          description: >
            You can turn on latency optimizations at some cost of quality. The
            best possible final latency varies by model. Possible values:

            0 - default mode (no latency optimizations)

            1 - normal latency optimizations (about 50% of possible latency
            improvement of option 3)

            2 - strong latency optimizations (about 75% of possible latency
            improvement of option 3)

            3 - max latency optimizations

            4 - max latency optimizations, but also with text normalizer turned
            off for even more latency savings (best latency, but can
            mispronounce eg numbers and dates).


            Defaults to None.
          required: false
          schema:
            type:
              - integer
              - 'null'
        - name: output_format
          in: query
          description: >-
            Output format of the generated audio. Formatted as
            codec_sample_rate_bitrate. So an mp3 with 22.05kHz sample rate at
            32kbs is represented as mp3_22050_32. MP3 with 192kbps bitrate
            requires you to be subscribed to Creator tier or above. PCM and WAV
            formats with 44.1kHz sample rate requires you to be subscribed to
            Pro tier or above. Note that the μ-law format (sometimes written
            mu-law, often approximated as u-law) is commonly used for Twilio
            audio inputs.
          required: false
          schema:
            $ref: >-
              #/components/schemas/V1TextToSpeechVoiceIdWithTimestampsPostParametersOutputFormat
            default: mp3_44100_128
        - name: xi-api-key
          in: header
          required: false
          schema:
            type: string
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AudioWithTimestampsResponseModel'
        '422':
          description: Validation Error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HTTPValidationError'
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Body_text_to_speech_full_with_timestamps'
servers:
  - url: https://api.elevenlabs.io
    description: Production
  - url: https://api.us.elevenlabs.io
    description: Production US
  - url: https://api.eu.residency.elevenlabs.io
    description: Production EU
  - url: https://api.in.residency.elevenlabs.io
    description: Production India
  - url: https://api.sg.residency.elevenlabs.io
    description: Production Singapore
components:
  schemas:
    V1TextToSpeechVoiceIdWithTimestampsPostParametersOutputFormat:
      type: string
      enum:
        - alaw_8000
        - mp3_22050_32
        - mp3_24000_48
        - mp3_44100_128
        - mp3_44100_192
        - mp3_44100_32
        - mp3_44100_64
        - mp3_44100_96
        - opus_48000_128
        - opus_48000_192
        - opus_48000_32
        - opus_48000_64
        - opus_48000_96
        - pcm_16000
        - pcm_22050
        - pcm_24000
        - pcm_32000
        - pcm_44100
        - pcm_48000
        - pcm_8000
        - ulaw_8000
        - wav_16000
        - wav_22050
        - wav_24000
        - wav_32000
        - wav_44100
        - wav_48000
        - wav_8000
      default: mp3_44100_128
      description: >-
        Output format of the generated audio. Formatted as
        codec_sample_rate_bitrate. So an mp3 with 22.05kHz sample rate at 32kbs
        is represented as mp3_22050_32. MP3 with 192kbps bitrate requires you to
        be subscribed to Creator tier or above. PCM and WAV formats with 44.1kHz
        sample rate requires you to be subscribed to Pro tier or above. Note
        that the μ-law format (sometimes written mu-law, often approximated as
        u-law) is commonly used for Twilio audio inputs.
      title: V1TextToSpeechVoiceIdWithTimestampsPostParametersOutputFormat
    VoiceSettingsResponseModel:
      type: object
      properties:
        stability:
          type:
            - number
            - 'null'
          format: double
          default: 0.5
          description: >-
            Determines how stable the voice is and the randomness between each
            generation. Lower values introduce broader emotional range for the
            voice. Higher values can result in a monotonous voice with limited
            emotion.
        use_speaker_boost:
          type:
            - boolean
            - 'null'
          default: true
          description: >-
            This setting boosts the similarity to the original speaker. Using
            this setting requires a slightly higher computational load, which in
            turn increases latency.
        similarity_boost:
          type:
            - number
            - 'null'
          format: double
          default: 0.75
          description: >-
            Determines how closely the AI should adhere to the original voice
            when attempting to replicate it.
        style:
          type:
            - number
            - 'null'
          format: double
          default: 0
          description: >-
            Determines the style exaggeration of the voice. This setting
            attempts to amplify the style of the original speaker. It does
            consume additional computational resources and might increase
            latency if set to anything other than 0.
        speed:
          type:
            - number
            - 'null'
          format: double
          default: 1
          description: >-
            Adjusts the speed of the voice. A value of 1.0 is the default speed,
            while values less than 1.0 slow down the speech, and values greater
            than 1.0 speed it up.
      title: VoiceSettingsResponseModel
    PronunciationDictionaryVersionLocatorRequestModel:
      type: object
      properties:
        pronunciation_dictionary_id:
          type: string
          description: The ID of the pronunciation dictionary.
        version_id:
          type:
            - string
            - 'null'
          description: >-
            The ID of the version of the pronunciation dictionary. If not
            provided, the latest version will be used.
      required:
        - pronunciation_dictionary_id
      title: PronunciationDictionaryVersionLocatorRequestModel
    BodyTextToSpeechFullWithTimestampsApplyTextNormalization:
      type: string
      enum:
        - auto
        - 'on'
        - 'off'
      default: auto
      description: >-
        This parameter controls text normalization with three modes: 'auto',
        'on', and 'off'. When set to 'auto', the system will automatically
        decide whether to apply text normalization (e.g., spelling out numbers).
        With 'on', text normalization will always be applied, while with 'off',
        it will be skipped.
      title: BodyTextToSpeechFullWithTimestampsApplyTextNormalization
    Body_text_to_speech_full_with_timestamps:
      type: object
      properties:
        text:
          type: string
          description: The text that will get converted into speech.
        model_id:
          type: string
          default: eleven_multilingual_v2
          description: >-
            Identifier of the model that will be used, you can query them using
            GET /v1/models. The model needs to have support for text to speech,
            you can check this using the can_do_text_to_speech property.
        language_code:
          type:
            - string
            - 'null'
          description: >-
            Language code (ISO 639-1) used to enforce a language for the model
            and text normalization. If the model does not support provided
            language code, an error will be returned.
        voice_settings:
          oneOf:
            - $ref: '#/components/schemas/VoiceSettingsResponseModel'
            - type: 'null'
          description: >-
            Voice settings overriding stored settings for the given voice. They
            are applied only on the given request.
        pronunciation_dictionary_locators:
          type: array
          items:
            $ref: >-
              #/components/schemas/PronunciationDictionaryVersionLocatorRequestModel
          description: >-
            A list of pronunciation dictionary locators (id, version_id) to be
            applied to the text. They will be applied in order. You may have up
            to 3 locators per request
        seed:
          type:
            - integer
            - 'null'
          description: >-
            If specified, our system will make a best effort to sample
            deterministically, such that repeated requests with the same seed
            and parameters should return the same result. Determinism is not
            guaranteed. Must be integer between 0 and 4294967295.
        previous_text:
          type:
            - string
            - 'null'
          description: >-
            The text that came before the text of the current request. Can be
            used to improve the speech's continuity when concatenating together
            multiple generations or to influence the speech's continuity in the
            current generation.
        next_text:
          type:
            - string
            - 'null'
          description: >-
            The text that comes after the text of the current request. Can be
            used to improve the speech's continuity when concatenating together
            multiple generations or to influence the speech's continuity in the
            current generation.
        previous_request_ids:
          type: array
          items:
            type: string
          description: >-
            A list of request_id of the samples that were generated before this
            generation. Can be used to improve the speech's continuity when
            splitting up a large task into multiple requests. The results will
            be best when the same model is used across the generations. In case
            both previous_text and previous_request_ids is send, previous_text
            will be ignored. A maximum of 3 request_ids can be send.
        next_request_ids:
          type: array
          items:
            type: string
          description: >-
            A list of request_id of the samples that come after this generation.
            next_request_ids is especially useful for maintaining the speech's
            continuity when regenerating a sample that has had some audio
            quality issues. For example, if you have generated 3 speech clips,
            and you want to improve clip 2, passing the request id of clip 3 as
            a next_request_id (and that of clip 1 as a previous_request_id) will
            help maintain natural flow in the combined speech. The results will
            be best when the same model is used across the generations. In case
            both next_text and next_request_ids is send, next_text will be
            ignored. A maximum of 3 request_ids can be send.
        use_pvc_as_ivc:
          type: boolean
          default: false
          description: >-
            If true, we won't use PVC version of the voice for the generation
            but the IVC version. This is a temporary workaround for higher
            latency in PVC versions.
        apply_text_normalization:
          $ref: >-
            #/components/schemas/BodyTextToSpeechFullWithTimestampsApplyTextNormalization
          default: auto
          description: >-
            This parameter controls text normalization with three modes: 'auto',
            'on', and 'off'. When set to 'auto', the system will automatically
            decide whether to apply text normalization (e.g., spelling out
            numbers). With 'on', text normalization will always be applied,
            while with 'off', it will be skipped.
        apply_language_text_normalization:
          type: boolean
          default: false
          description: >-
            This parameter controls language text normalization. This helps with
            proper pronunciation of text in some supported languages. WARNING:
            This parameter can heavily increase the latency of the request.
            Currently only supported for Japanese.
      required:
        - text
      title: Body_text_to_speech_full_with_timestamps
    CharacterAlignmentResponseModel:
      type: object
      properties:
        characters:
          type: array
          items:
            type: string
        character_start_times_seconds:
          type: array
          items:
            type: number
            format: double
        character_end_times_seconds:
          type: array
          items:
            type: number
            format: double
      required:
        - characters
        - character_start_times_seconds
        - character_end_times_seconds
      title: CharacterAlignmentResponseModel
    AudioWithTimestampsResponseModel:
      type: object
      properties:
        audio_base64:
          type: string
          description: Base64 encoded audio data
        alignment:
          oneOf:
            - $ref: '#/components/schemas/CharacterAlignmentResponseModel'
            - type: 'null'
          description: Timestamp information for each character in the original text
        normalized_alignment:
          oneOf:
            - $ref: '#/components/schemas/CharacterAlignmentResponseModel'
            - type: 'null'
          description: Timestamp information for each character in the normalized text
      required:
        - audio_base64
      title: AudioWithTimestampsResponseModel
    ValidationErrorLocItems:
      oneOf:
        - type: string
        - type: integer
      title: ValidationErrorLocItems
    ValidationError:
      type: object
      properties:
        loc:
          type: array
          items:
            $ref: '#/components/schemas/ValidationErrorLocItems'
        msg:
          type: string
        type:
          type: string
      required:
        - loc
        - msg
        - type
      title: ValidationError
    HTTPValidationError:
      type: object
      properties:
        detail:
          type: array
          items:
            $ref: '#/components/schemas/ValidationError'
      title: HTTPValidationError

```

## Examples



**Request**

```json
{
  "text": "This is a test for the API of ElevenLabs."
}
```

**Response**

```json
{
  "audio_base64": "base64_encoded_audio_string",
  "alignment": {
    "characters": [
      "H",
      "e",
      "l",
      "l",
      "o"
    ],
    "character_start_times_seconds": [
      0,
      0.1,
      0.2,
      0.3,
      0.4
    ],
    "character_end_times_seconds": [
      0.1,
      0.2,
      0.3,
      0.4,
      0.5
    ]
  },
  "normalized_alignment": {
    "characters": [
      "H",
      "e",
      "l",
      "l",
      "o"
    ],
    "character_start_times_seconds": [
      0,
      0.1,
      0.2,
      0.3,
      0.4
    ],
    "character_end_times_seconds": [
      0.1,
      0.2,
      0.3,
      0.4,
      0.5
    ]
  }
}
```

**SDK Code**

```typescript
import { ElevenLabsClient } from "@elevenlabs/elevenlabs-js";

async function main() {
    const client = new ElevenLabsClient();
    await client.textToSpeech.convertWithTimestamps("voice_id", {
        text: "This is a test for the API of ElevenLabs.",
    });
}
main();

```

```python
from elevenlabs import ElevenLabs

client = ElevenLabs()

client.text_to_speech.convert_with_timestamps(
    voice_id="voice_id",
    text="This is a test for the API of ElevenLabs.",
)

```

```go
package main

import (
	"fmt"
	"strings"
	"net/http"
	"io"
)

func main() {

	url := "https://api.elevenlabs.io/v1/text-to-speech/voice_id/with-timestamps"

	payload := strings.NewReader("{\n  \"text\": \"This is a test for the API of ElevenLabs.\"\n}")

	req, _ := http.NewRequest("POST", url, payload)

	req.Header.Add("Content-Type", "application/json")

	res, _ := http.DefaultClient.Do(req)

	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)

	fmt.Println(res)
	fmt.Println(string(body))

}
```

```ruby
require 'uri'
require 'net/http'

url = URI("https://api.elevenlabs.io/v1/text-to-speech/voice_id/with-timestamps")

http = Net::HTTP.new(url.host, url.port)
http.use_ssl = true

request = Net::HTTP::Post.new(url)
request["Content-Type"] = 'application/json'
request.body = "{\n  \"text\": \"This is a test for the API of ElevenLabs.\"\n}"

response = http.request(request)
puts response.read_body
```

```java
import com.mashape.unirest.http.HttpResponse;
import com.mashape.unirest.http.Unirest;

HttpResponse<String> response = Unirest.post("https://api.elevenlabs.io/v1/text-to-speech/voice_id/with-timestamps")
  .header("Content-Type", "application/json")
  .body("{\n  \"text\": \"This is a test for the API of ElevenLabs.\"\n}")
  .asString();
```

```php
<?php
require_once('vendor/autoload.php');

$client = new \GuzzleHttp\Client();

$response = $client->request('POST', 'https://api.elevenlabs.io/v1/text-to-speech/voice_id/with-timestamps', [
  'body' => '{
  "text": "This is a test for the API of ElevenLabs."
}',
  'headers' => [
    'Content-Type' => 'application/json',
  ],
]);

echo $response->getBody();
```

```csharp
using RestSharp;

var client = new RestClient("https://api.elevenlabs.io/v1/text-to-speech/voice_id/with-timestamps");
var request = new RestRequest(Method.POST);
request.AddHeader("Content-Type", "application/json");
request.AddParameter("application/json", "{\n  \"text\": \"This is a test for the API of ElevenLabs.\"\n}", ParameterType.RequestBody);
IRestResponse response = client.Execute(request);
```

```swift
import Foundation

let headers = ["Content-Type": "application/json"]
let parameters = ["text": "This is a test for the API of ElevenLabs."] as [String : Any]

let postData = JSONSerialization.data(withJSONObject: parameters, options: [])

let request = NSMutableURLRequest(url: NSURL(string: "https://api.elevenlabs.io/v1/text-to-speech/voice_id/with-timestamps")! as URL,
                                        cachePolicy: .useProtocolCachePolicy,
                                    timeoutInterval: 10.0)
request.httpMethod = "POST"
request.allHTTPHeaderFields = headers
request.httpBody = postData as Data

let session = URLSession.shared
let dataTask = session.dataTask(with: request as URLRequest, completionHandler: { (data, response, error) -> Void in
  if (error != nil) {
    print(error as Any)
  } else {
    let httpResponse = response as? HTTPURLResponse
    print(httpResponse)
  }
})

dataTask.resume()
```