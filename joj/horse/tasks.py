from celery import Celery

celery_app = Celery('tasks', broker='pyamqp://localhost//')

celery_app.conf.update({
    'result_backend': 'rpc://',
    'result_persistent': False,
    'task_routes': ([
        ('joj.tiger.*', {'queue': 'tiger'}),
        ('joj.horse.*', {'queue': 'horse'}),
    ], )
})

@celery_app.task(name='joj.horse.compile')
def compile_task_end(result):
    print(result)


if __name__ == '__main__':
    celery_app.worker_main()
