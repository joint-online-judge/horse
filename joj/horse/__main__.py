# import click
import uvicorn

from joj.horse import app
from joj.horse.config import cli_command
from joj.horse.utils.db import get_db


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

# @click.pass_context
# def test(ctx):
#     print(ctx.params['verbose'])
#
#
# @click.command()
# @click.option('--verbose', '-v', is_flag=True, help='Enables verbose mode.')
# @click.argument('args', nargs=-1)
# def main(args, **kwargs):
#     print(*args)
#     test()
#     app.run(host="0.0.0.0", port=34765, debug=True, auto_reload=True)

@cli_command()
def main():
    db = get_db()
    uvicorn.run(app, host="0.0.0.0", port=34765)


if __name__ == "__main__":
    main()
