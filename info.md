# Mnemos for Home Assistant

A HACS integration that makes it trivial to send a snapshot to a [Mnemos](https://github.com/vithurshan-selvarajah/mnemos) face-recognition backend and react to the matched person(s) in your automations.

> Pronounced **nee-MOZ** — the Greek goddess of memory.

## What you get

- `mnemos.identify` action — send an image (from a `camera.*` entity **or** a local file path) to Mnemos.
- Action **response** with **all** matched persons (name, confidence) and a boolean `unknown` flag. Read it via the `response` variable in scripts, or the `Last identify` sensor for ad-hoc inspection.
- `binary_sensor.mnemos_<host>_reachable` — is the backend healthy?
- `sensor.mnemos_<host>_model` — currently active model + live reindex progress.
- `sensor.mnemos_<host>_last_identify` — most recent top match, with the full payload in attributes.

## Quick example

```yaml
automation:
  - alias: "Greet known faces at the door"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_motion
        to: "on"
    action:
      - alias: "Send snapshot to Mnemos and read response"
        response_variable: identify_result
        action: mnemos.identify
        data:
          entity_id: camera.front_door
      - if:
          - condition: template
            value_template: >
              {{ (identify_result.persons | default([])) | length > 0
                 and identify_result.persons[0].confidence > 0.75 }}
        then:
          - action: tts.speak
            data:
              media_player_entity_id: tts.living_room
              message: >-
                Hello {{ identify_result.persons[0].name }}!
              # confidence-aware template:
              # {% if identify_result.persons[0].confidence > 0.75 %}
```

## Configuration

1. Install via HACS (custom repository → add `vithurshan-selvarajah/Mnemos-HA`).
2. Add the **Mnemos** integration.
3. Enter the Mnemos backend URL (default `http://mnemos-backend:8000` — works if HA can resolve the Docker service name) and an API key.
4. An **Identify-Only** API key from the Mnemos frontend is sufficient.

## Documentation

See [README.md](README.md) for the full reference and troubleshooting.
