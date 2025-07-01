from flask import Flask, render_template, redirect, url_for, request, flash, Response
import docker
from docker import errors

app = Flask(__name__)
app.secret_key = 'supersecretkey' 
client = docker.DockerClient(base_url='unix://var/run/docker.sock')

BOTS = [
    {'name': 'bonus-bot', 'label': 'Bonus Bot'},
    {'name': 'leaderboard-bot', 'label': 'Leaderboard Bot'},
    {'name': 'weekly-bot', 'label': 'Weekly Bot'},
]

def get_status(container_name):
    try:
        container = client.containers.get(container_name)
        return container.status
    except errors.NotFound:
        return 'not found'
    except Exception as e:
        return f'error: {e}'

@app.route('/')
def index():
    bots = []
    for bot in BOTS:
        status = get_status(bot['name'])
        bots.append({**bot, 'status': status})
    return render_template('index.html', bots=bots)

@app.route('/start/<bot_name>', methods=['POST'])
def start_bot(bot_name):
    try:
        container = client.containers.get(bot_name)
        
        # Останавливаем контейнер если он запущен
        if container.status == 'running':
            container.stop()
        
        # Запускаем контейнер
        container.start()
        
        bot_commands = {
            'bonus-bot': 'python bonus_bot.py',
            'leaderboard-bot': 'python leaderboard_bot.py', 
            'weekly-bot': 'python weekly_bot.py'
        }
        
        if bot_name in bot_commands:
            container.exec_run(bot_commands[bot_name], detach=True)
        
        flash(f'{bot_name} запущен!', 'success')
    except Exception as e:
        flash(f'Ошибка запуска {bot_name}: {e}', 'danger')
    return redirect(url_for('index'))

@app.route('/stop/<bot_name>', methods=['POST'])
def stop_bot(bot_name):
    try:
        container = client.containers.get(bot_name)
        container.stop()
        flash(f'{bot_name} остановлен!', 'success')
    except Exception as e:
        flash(f'Ошибка остановки {bot_name}: {e}', 'danger')
    return redirect(url_for('index'))

@app.route('/logs/<bot_name>')
def view_logs(bot_name):
    try:
        container = client.containers.get(bot_name)
        # Читаем последние 100 строк файла bot.log внутри контейнера
        exec_result = container.exec_run('tail -n 100 bot.log')
        log_content = exec_result.output.decode('utf-8') if exec_result.exit_code == 0 else 'Логи не найдены или ошибка доступа.'
    except Exception as e:
        log_content = f'Ошибка: {e}'
    return render_template('logs.html', bot_name=bot_name, log_content=log_content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
