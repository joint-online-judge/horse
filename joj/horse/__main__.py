from joj.horse import app


# @app.route("/")
# async def test(request):
#     return json({"hello": "world"})
#
#
# @app.route("/compile")
# async def do_compile(request):
#     task = celery_app.signature('joj.tiger.compile', link=compile_task_end.s())
#     result = task.apply_async(['message'])
#     # result.forget()
#     # print(result.get())
#     return json({"hello": "world"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=34765, debug=True, auto_reload=True)
