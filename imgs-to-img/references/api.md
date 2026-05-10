# Duomi Nano Banana API Reference

## Environment

- `DUOMI_API_AUTHORIZATION`: required `Authorization` header value
- `DUOMI_API_BASE_URL`: optional base URL override, defaults to `https://duomiapi.com`
- `DUOMI_API_COOKIE`: optional `Cookie` header, sent only when present

## HTTPS Behavior

- The script uses normal HTTPS verification first.
- If the local Python certificate store rejects the remote certificate with `CERTIFICATE_VERIFY_FAILED`, the script retries once with an unverified SSL context.
- This fallback exists to keep the skill usable on machines where Python's trust store is incomplete even though the API endpoint is otherwise reachable.

## Create Task

- Method: `POST`
- Path: `/api/gemini/nano-banana-edit`
- Default model used by the script: `nano-banana-pro`

Example request body:

```json
{
  "model": "nano-banana-pro",
  "prompt": "这个美女悠闲的躺在落叶上",
  "image_urls": [
    "https://img.tusij.com/example-1.jpg",
    "https://img.tusij.com/example-2.jpg"
  ],
  "aspect_ratio": "",
  "image_size": "1K"
}
```

Expected success response:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "task_id": "6cf733cd-d8f8-b0da-2ad0-3b4edfc9f35a"
  }
}
```

The script treats `code=200`, `msg=success`, and a non-empty `data.task_id` as the required success contract.

## Preview Parameters

- CLI flag: `--preview-params`
- Behavior: run the CLI with `--preview-params` to inspect the effective `model`, `aspect_ratio`, and `image_size` before any task is created
- The preview step does not submit a Duomi task
- The confirmation flow is preview-first: collect prompt and image URLs, preview the effective parameters, ask the user to confirm or change only `model`, `aspect_ratio`, and `image_size`, then create the task after confirmation

## Query Task

- Method: `GET`
- Path: `/api/gemini/nano-banana/{task_id}`
- Default polling interval in the script: `10` seconds

Expected success response:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "task_id": "6cf733cd-d8f8-b0da-2ad0-3b4edfc9f35a",
    "state": "succeeded",
    "data": {
      "images": [
        {
          "url": "https://d22p6zz7asihrw.cloudfront.net/uploads/output.png",
          "file_name": "output.png"
        }
      ],
      "description": ""
    },
    "create_time": "1777968682",
    "update_time": "1777968734",
    "msg": "",
    "status": "3",
    "action": "generate"
  }
}
```

## State Handling

- `state=succeeded`: final result is ready and the first image URL becomes `primary_image_url`
- `state=failed`, `state=error`, `state=cancelled`: terminal failure, surface an error
- Known running states accepted by the script: `pending`, `queued`, `running`, `processing`
- Missing or unknown `state` values are treated as response-contract errors rather than silent retries

## CLI Follow-Up Modes

- Preview the effective parameters before submission:
  - `--preview-params`
- Create a new task after confirmation and keep waiting:
  - `--prompt ... --image-url ...`
- Create a new task after confirmation and return immediately:
  - `--prompt ... --image-url ... --no-wait`
- Reattach to an existing task and keep polling:
  - `--task-id <task_id>`
- Reattach to an existing task and inspect it once:
  - `--task-id <task_id> --no-wait`

When reattaching, the script uses the supplied `task_id` and resumes polling without creating a new task.

## Output Mapping

The script returns:

- `task_id` from `data.task_id`
- `state` from `data.state`
- `status` from `data.status`
- `primary_image_url` from `data.data.images[0].url`
- `images` from `data.data.images`
- `description` from `data.data.description`
- `raw_create_response` and `raw_query_response` for debugging

When the script is reattached with `--task-id`, `raw_create_response` is `null` because no create request is made in that invocation.
