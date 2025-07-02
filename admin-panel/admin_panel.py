import docker
import os

from flask import Flask, render_template, redirect, url_for, request, flash, Response

from docker import errors
from database import Database

from dotenv import load_dotenv

load_dotenv()

POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

def get_db():
    return Database(
        minconn=1,
        maxconn=5,
        dbname=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT')
    )

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

@app.route('/owners', methods=['GET', 'POST'])
def owners():
    db = get_db()
    if request.method == 'POST':
        if 'add' in request.form:
            try:
                channel_id = int(request.form['channel_id'])
                username = request.form['username']
                update_chat_id = int(request.form['update_chat_id'])
                group_number = int(request.form['group_number'])
                db.add_channel_owner(channel_id, username, update_chat_id, group_number)
                flash('Запись успешно добавлена!', 'success')
            except Exception as e:
                flash(f'Ошибка добавления: {e}', 'danger')
        elif 'delete' in request.form:
            try:
                channel_id = int(request.form['delete'])
                db.delete_channel_owner(channel_id)
                flash('Запись успешно удалена!', 'success')
            except Exception as e:
                flash(f'Ошибка удаления: {e}', 'danger')
        return redirect(url_for('owners'))
    # Получаем все строки и имена столбцов
    rows = db.execute_read_many_query('SELECT * FROM channel_owners')
    columns = []
    if rows:
        conn = db.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM channel_owners LIMIT 1')
                columns = [desc[0] for desc in cursor.description]
        finally:
            db.release_connection(conn)
    return render_template('owners.html', rows=rows, columns=columns)

@app.route('/bonus', methods=['GET', 'POST'])
def bonus():
    db = get_db()
    if request.method == 'POST':
        if 'add' in request.form:
            try:
                profit = int(request.form['profit'])
                commission = int(request.form['commission'])
                db.add_bonus(profit, commission)
                flash('Bonus threshold added!', 'success')
            except Exception as e:
                flash(f'Error adding bonus: {e}', 'danger')
        elif 'delete' in request.form:
            try:
                profit = int(request.form['delete'])
                db.delete_bonus(profit)
                flash('Bonus threshold deleted!', 'success')
            except Exception as e:
                flash(f'Error deleting bonus: {e}', 'danger')
        elif 'edit' in request.form:
            try:
                profit = int(request.form['profit'])
                commission = int(request.form['commission'])
                db.update_bonus(profit, commission)
                flash('Bonus threshold updated!', 'success')
            except Exception as e:
                flash(f'Error updating bonus: {e}', 'danger')
        return redirect(url_for('bonus'))
    rows = db.get_all_bonus()
    columns = ['profit', 'commission']
    return render_template('bonus.html', rows=rows, columns=columns)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
