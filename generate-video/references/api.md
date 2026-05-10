# MagicLight Video API Reference

## Environment

- `MAGIC_SVC_KEY`: request header value for `Magic-Svc-Key`
- `MAGIC_SVC_AUTH`: request header value for `Magic-Svc-Auth`
- `MAGIC_USER_ID`: default `user_id` sent in requests
- `MAGIC_API_BASE_URL`: optional override, defaults to `http://server-test.magiclight.ai`

## Create Endpoint

- `POST /task-schedule/open_task/create`

Example payload:

```json
{
  "type": "i2v",
  "user_id": "user-id",
  "param": {
    "ratio": 1,
    "definition": "720",
    "duration": 5,
    "image2video_pro_type": "seedance2_0",
    "enable_audio": true,
    "prompt": "图中的人物在游泳池自由泳，保持人物面部细节不变",
    "img_url": "https://example.com/source.jpg"
  }
}
```

Expected create response:

```json
{
  "biz_code": 10000,
  "msg": "Success",
  "data": {
    "type": "i2v",
    "user_id": "user-id",
    "task_id": "2049736095785779200",
    "status": 1,
    "source_url": "",
    "need_query": true
  }
}
```

## Query Endpoint

- `GET /task-schedule/open_task/get?user_id=<user_id>&task_id=<task_id>`

Expected query response:

```json
{
  "biz_code": 10000,
  "msg": "Success",
  "data": {
    "type": "i2v",
    "user_id": "user-id",
    "task_id": "2049736095785779200",
    "status": 2,
    "result": {
      "video_url": "https://i2v.magiclight.ai/2049736095785779200/2049736095785779200_56ea72.mp4"
    },
    "error_code": "",
    "error_message": ""
  }
}
```

## Status Handling

- `status=1`: running, keep polling
- `status=2`: success, use `data.result.video_url`
- Any other status: treat as failure and surface `error_code` / `error_message`
