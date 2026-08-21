---

title: SpeechifyAI Build
headline: 'SpeechifyAI Build: TTS, Voices, Streaming, and SSML'
subtitle: >-
Build speech into your product with one API. Generate audio, stream long-form
text, clone voices, and control delivery with SSML.
description: >-
Use SpeechifyAI Build to generate speech, stream long-form audio, clone
voices, and control delivery with SSML.
---------------------------------------

## Your first request

<EndpointRequestSnippet endpoint="POST /v1/audio/speech" />

Ready to run it end to end? The [Quickstart](/build/guides/get-started/quickstart) walks you through your first call: get a key, install the SDK, generate speech, and play it.

<Tip>
  Grab an API key at 

  [platform.speechify.ai/api-keys](https://platform.speechify.ai/api-keys)

   and set 

  `SPEECHIFY_API_KEY`

   so the SDKs authenticate automatically.
</Tip>

## Set up

<CardGroup cols={2}>
  <Card title="Install an SDK" icon="fa-regular fa-cube" href="/build/guides/get-started/official-sdks">
    `pip install speechify-api` for Python, `npm install @speechify/api` for TypeScript. Both read `SPEECHIFY_API_KEY` from the environment automatically.
  </Card>

  <Card title="Authenticate" icon="fa-regular fa-key" href="/build/guides/get-started/authentication">
    A single `Authorization: Bearer` key works for every endpoint. Manage and rotate keys in the console.
  </Card>
</CardGroup>

## Build With Speech

<CardGroup cols={2}>
  <Card title="Streaming" icon="fa-regular fa-play" href="/build/guides/text-to-speech/streaming">
    Start playback before the full audio is generated. Up to 20,000 characters per request.
  </Card>

  <Card title="Voice cloning" icon="fa-regular fa-microphone-lines" href="/build/guides/voice-cloning/overview">
    Clone a voice from a 10-30 second sample, with verified consent from the speaker. Cloned voices work across every supported language.
  </Card>

  <Card title="SSML and emotion" icon="fa-regular fa-file-code" href="/build/guides/text-to-speech/ssml">
    Fine-grained control over pitch, rate, pauses, emphasis, and 13 emotion presets.
  </Card>

  <Card title="Speech marks" icon="fa-regular fa-location-crosshairs" href="/build/guides/text-to-speech/speech-marks">
    Word-level timestamps for highlighting, captions, and audio-text sync.
  </Card>
</CardGroup>

## Integrations

Speechify voices drop into every major voice-agent platform. Native plugins where they exist, an open-source [`tts-shims`](https://github.com/Speechify-AI/tts-shims) proxy where they don't.

<CardGroup cols={3}>
  <Card title="LiveKit" icon="fa-regular fa-tower-broadcast" href="/build/guides/integrations/livekit">
    Add `speechify.TTS(...)` to a LiveKit `AgentSession` via the official Python plugin.
  </Card>

  <Card title="Vapi" icon="fa-regular fa-phone" href="/build/guides/integrations/vapi">
    Serve Speechify PCM to Vapi custom voice via the `tts-shims` Vapi provider.
  </Card>

  <Card title="Deepgram" icon="fa-regular fa-headphones" href="/build/guides/integrations/deepgram">
    Point Deepgram Voice Agent's `open_ai` speak provider at the `tts-shims` shim.
  </Card>
</CardGroup>

See the [Integrations overview](/build/guides/integrations) for the platform picker.

## Models and languages

| Model                | Best for                                 | Languages            | Highlights                                                                                                                     |
| -------------------- | ---------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `simba-3.2`          | Recommended for new English integrations | English              | Lowest TTFB, richest expressivity; the recommended Simba 3 model                                                               |
| `simba-3.0`          | Streaming-native beyond English          | English + 6 European | The API default when `model` is omitted; German, Spanish, French, Italian and Brazilian Portuguese, set `language` to pick one |
| `simba-multilingual` | Multilingual and mixed-language input    | 30+                  | Same voice IDs across every language, no separate cloning required                                                             |
| `simba-english`      | Legacy English integrations              | English              | Kept for compatibility with integrations that name it explicitly; accepts cloned/personal voices self-serve                    |

See [Models](/build/guides/concepts/models) and [Language Support](/build/guides/text-to-speech/language-support) for the full matrix.

## Resources

<CardGroup cols={3}>
  <Card title="API Reference" icon="fa-regular fa-book-open" href="/build/api-reference">
    Endpoint schemas, parameters, and response shapes.
  </Card>

  <Card title="Examples" icon="fa-brands fa-github" href="https://github.com/SpeechifyInc/ai-api-examples">
    End-to-end demo projects on GitHub.
  </Card>

  <Card title="Console" icon="fa-regular fa-sliders" href="https://platform.speechify.ai">
    Manage API keys, voices, and billing.
  </Card>
</CardGroup>
