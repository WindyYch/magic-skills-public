# MagicLight Image API Reference

## Environment

- `MAGIC_SVC_KEY`: request header value for `Magic-Svc-Key`
- `MAGIC_SVC_AUTH`: request header value for `Magic-Svc-Auth`
- `MAGIC_USER_ID`: default `user_id` sent in requests
- `MAGIC_API_BASE_URL`: optional override, defaults to `http://server-test.magiclight.ai`

## Endpoint

- `POST /task-schedule/open_task/create`

## Text-to-Image Payload

```json
{
  "type": "t2i",
  "user_id": "user-id",
  "task_id": "generated-task-id",
  "param": {
    "prompt": "A cinematic toy astronaut walking on a strawberry planet, ultra detailed, soft lighting",
    "aspect_ratio": "9:16",
    "model": "gemini-2.5-flash-image"
  }
}
```

## Image-to-Image Payload

```json
{
  "type": "i2i",
  "user_id": "user-id",
  "task_id": "generated-task-id",
  "param": {
    "prompt": "Keep the character identity, change the outfit to a white space suit, sunset background, more cinematic",
    "image_url": "https://example.com/source.jpg",
    "image_mime_type": "image/jpg",
    "aspect_ratio": "16:9",
    "model": "gemini-2.5-flash-image"
  }
}
```

## Success Response Shape

Image tasks return synchronously. The script should prefer:

1. `data.source_url`
2. `data.result.images[0].url`

Example:

```json
{
  "biz_code": 10000,
  "msg": "Success",
  "data": {
    "type": "t2i",
    "user_id": "user-id",
    "task_id": "123321",
    "status": 2,
    "source_url": "https://images.magiclight.ai/open-task/123321/0.png",
    "need_query": false,
    "result": {
      "images": [
        {
          "url": "https://images.magiclight.ai/open-task/123321/0.png",
          "mime_type": "image/png"
        }
      ],
      "model": "gemini-2.5-flash-image",
      "text": "Here is a cinematic toy astronaut walking on a strawberry planet:"
    }
  }
}
```
