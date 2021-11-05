import json


def objectToJsonStr(obj) -> str:
    return json.dumps(obj,
                      sort_keys=True,
                      indent=4,
                      separators=(", ", ": "),
                      ensure_ascii=False
                      )


def strToJsonStr(s: str) -> str:
    try:
        return objectToJsonStr(json.loads(s))
    except:
        return s.replace("'", '"').replace("：", ":")\
            .replace("“", '"').replace("”", '"').replace("，", ",")\
            .replace("【", "[").replace("】", "]")


def errorToDict(errorStr: str) -> dict:
    return dict(error=errorStr)


def errorToJsonStr(errorStr: str) -> str:
    return objectToJsonStr(errorToDict(errorStr))
