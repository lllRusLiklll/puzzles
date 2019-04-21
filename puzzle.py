from flask import Flask, request
import logging
import json
import random

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

puzzles = {
    'слон': ['У этого зверя огромный рост, cзади у зверя — маленький хвост, cпереди у зверя — хвост большой. Кто же это? Кто же это? Кто такой? Ну, конечно, это он! Ну, конечно, это ...', "1540737/df8d524f77d4b9d9d311"],
    'жираф': ['Достает своей макушкой у деревьев до верхушки, шея, как высокий шкаф, добрый, в пятнышках …', "937455/7698f9cee3aa65045094"],
    'олень': ['Кто на своей голове лес носит?', "965417/ef6659b355d504d47f84"],
    'рысь': ['Не боюсь я слова "брысь", - я лесная кошка …', "965417/62519652cc083e798f78"],
    'белка': ['Кто на ветке шишки грыз и бросал объедки вниз?', "1652229/b6d07ba4138cc07f1064"],
    'коала': ['Посмотрите, посмотрите - он повис на эвкалипте! Зверек такой забавный, медвежонок славный.', "965417/310e7e04fded3be6995d"]
}

N = len(puzzles)

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return json.dumps(response)


def handle_dialog(res, req):
    global N
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        res['response']['buttons'] = [
            {
                'title': 'Помощь',
                'hide': True
            }
        ]
        sessionStorage[user_id] = {
            'first_name': None,  # здесь будет храниться имя
            'game_started': False  # здесь информация о том, что пользователь начал игру. По умолчанию False
        }
        return

    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if 'помощь' in req['request']['nlu']['tokens']:
                    res['response']['text'] = 'Справка: Я буду загадывать загадки, а ты должен отгадывать. Так, как тебя зовут?'        
        elif first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['guessed_puzzles'] = []
            # как видно из предыдущего навыка, сюда мы попали, потому что пользователь написал своем имя.
            # Предлагаем ему сыграть и два варианта ответа "Да" и "Нет".
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Поотгадываешь загадки?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                },
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
    else:
        # У нас уже есть имя, и теперь мы ожидаем ответ на предложение сыграть.
        # В sessionStorage[user_id]['game_started'] хранится True или False в зависимости от того,
        # начал пользователь игру или нет.
        if not sessionStorage[user_id]['game_started']:
            # игра не начата, значит мы ожидаем ответ на предложение сыграть.
            if 'да' in req['request']['nlu']['tokens']:
                # если пользователь согласен, то проверяем не отгадал ли он уже все загадки.
                # здесь окажутся и пользователи, которые уже отгадывали загадки
                if len(sessionStorage[user_id]['guessed_puzzles']) == N:
                    # если все N загадок отгаданы, то заканчиваем игру
                    res['response']['text'] = 'Ты отгадал все загадки!'
                    res['end_session'] = True
                else:
                    # если есть неотгаданные загадки, то продолжаем игру
                    sessionStorage[user_id]['game_started'] = True
                    # номер попытки, чтобы показывать фото по порядку
                    sessionStorage[user_id]['attempt'] = 1
                    # функция, которая выбирает загадку для игры и показывает фото
                    play_game(res, req)
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно!'
                res['end_session'] = True
            elif 'помощь' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Справка: Я буду загадывать загадки, а ты должен отгадывать. Так что, поотгадываешь загадки?'
            else:
                res['response']['text'] = 'Не поняла ответа! Так да или нет?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    }
                ]
        else:
            play_game(res, req)
            
            
def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    if attempt == 1:
        # если попытка первая, то случайным образом выбираем загадку для гадания
        puzzle = random.choice(list(puzzles))
        # выбираем его до тех пор пока не выбираем загадку, которого нет в sessionStorage[user_id]['guessed_puzzles']
        while puzzle in sessionStorage[user_id]['guessed_puzzles']:
            puzzle = random.choice(list(puzzles))
        # записываем загадку в информацию о пользователе
        sessionStorage[user_id]['puzzle'] = puzzle
        # добавляем в ответ загадку
        res['response']['text'] = puzzles[puzzle][0]
    else:
        # сюда попадаем, если попытка отгадать не первая
        puzzle = sessionStorage[user_id]['puzzle']
        # проверяем есть ли правильный ответ в сообщение
        if puzzle in req['request']['nlu']['tokens']:
            # если да, то добавляем загадку к sessionStorage[user_id]['guessed_puzzles'] и
            # отправляем пользователя на второй круг.
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            res['response']['card']['title'] = 'Правильно! Это - %s. Cыграем ещё?' % (puzzle)
            res['response']['card']['image_id'] = puzzles[puzzle][1]
            res['response']['text'] = 'Cыграем ещё?'
            res['response']['buttons'] = [
                    {
                        "title": "Кто это такой?",
                        "url": "https://ru.wikipedia.org/wiki/" + puzzle,
                        "hide": True
                    }              
                ]
            sessionStorage[user_id]['guessed_puzzles'].append(puzzle)
            sessionStorage[user_id]['game_started'] = False
            return
        else:
            # если нет
            if attempt == 4:
                # если попытка третья, то значит, что все картинки мы показали.
                # В этом случае говорим ответ пользователю,
                # добавляем загадку к sessionStorage[user_id]['guessed_puzzles'] и отправляем его на второй круг.
                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['title'] = 'Вы пытались. Это %s. Сыграем ещё?' % (puzzle)
                res['response']['card']['image_id'] = puzzles[puzzle][1]
                res['response']['text'] = 'Cыграем ещё?'
                res['response']['buttons'] = [
                    {
                        "title": "Кто это такой?",
                        "url": "https://ru.wikipedia.org/wiki/" + puzzle,
                        "hide": True
                    }              
                ]
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['guessed_puzzles'].append(puzzle)
                return
            else:
                res['response']['text'] = 'А вот и не угадал!'
    # увеличиваем номер попытки доля следующего шага
    sessionStorage[user_id]['attempt'] += 1


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name', то возвращаем её значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()