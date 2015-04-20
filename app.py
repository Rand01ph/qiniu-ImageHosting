# -*- coding: utf-8 -*-
__author__ = 'Rand01ph'

from flask import Flask, request, g, make_response, render_template, abort, Response, redirect
from pymongo import MongoClient, errors
from bson import binary, objectid, errors
from cStringIO import StringIO
from PIL import Image
import datetime
import hashlib
from qiniu import Auth

ACCESS_KEY = 'kQq_79vkobbT7g_RZjjqzn9utZ2se701E4Ff970P'
SECRET_KEY = 'lJ639U6O9gUuWfAHHiGnD6Yv-QgUdnRExDEEz_GB'

app = Flask(__name__)
app.config.from_object(__name__)
app.debug = True

q = Auth(access_key=app.config.get('ACCESS_KEY'), secret_key=app.config.get('SECRET_KEY'))

db = MongoClient('localhost', 27017).test

allow_formats = set(['jpeg', 'png', 'gif'])


def save_file(f):
	content = StringIO(f.read())
	try:
		mime = Image.open(content).format.lower()
		if mime not in allow_formats:
			raise IOError()
	except IOError:
		abort(400)

	sha1 = hashlib.sha1(content.getvalue()).hexdigest()
	c = dict(
		content=binary.Binary(content.getvalue()),
		mime=mime,
		time=datetime.datetime.utcnow(),
		sha1=sha1,
	)
	try:
		db.files.save(c)
	except pymongo.errors.DuplicateKeyError:
		pass
	return sha1


@app.route('/f/<sha1>')
def serve_file(sha1):
	import bson.errors

	try:
		f = db.files.find_one({'sha1': sha1})
		if f is None:
			raise bson.errors.InvalidId()
		if request.headers.get('If-Modified-Since') == f['time'].ctime():
			return Response(status=304)
		resp = Response(f['content'], mimetype='image/' + f['mime'])
		resp.headers['Last-Modified'] = f['time'].ctime()
		return resp
	except bson.errors.InvalidId:
		abort(404)


@app.route('/upload', methods=['post'])
def upload():
	f = request.files['uploaded_file']
	sha1 = save_file(f)
	return redirect('/f/' + str(sha1))


@app.route('/')
def index():
	return render_template('index.html')


@app.route('/browser')
def browser():
	user_agent = request.headers.get('User-Agent')
	return u'<p>你的浏览器是：%s<p>' % user_agent


if __name__ == '__main__':
	app.run(port=7777)

