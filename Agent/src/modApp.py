"""
WHAT: A module for the primary entry point of the API
WHY: This is the Flask standard entry point, using an 'modApp.py'
ASSUMES: Listens on IP and ports listed below
FUTURE IMPROVEMENTS: Remove "waitress" and replace with "uwsgi" for better web app serving and control
WHO: SL 2020-09-10
"""

import modConfig
from waitress import serve
from paste.translogger import TransLogger
from flask import Flask, redirect, url_for
from flask_compress import Compress
from modDatabase import db
from werkzeug.middleware.proxy_fix import ProxyFix
from apis.v1_3 import blueprint as blueprint_v1_3
import traceback


def appFactory():
    """
    Method to create the flask app without binding to the database to:
    * separate concerns
    * avoid circular import references
    :return: Flask app object
    """

    # create flask app object with a name
    app = Flask(__name__)

    app.url_map.strict_slashes = False

    # add compression
    Compress(app)

    # required so we can get client IP address in logs
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # register versions
    app.register_blueprint(blueprint_v1_3)

    # store database config
    app.config.update(modConfig.dbConfig)

    return app


app = appFactory()  # create flask app object
db.init_app(app)  # bind to database


@app.route('/')
def redirectVersion():
    """
    Redirects user to the swagger page of the latest version of the api
    :return: A redirect
    """
    return redirect(url_for('%s.doc' % modConfig.defaultVersion))


@app.route('/health')
def healthCheck():
    """
    An endpoint that checks the api is responding and the databases are responding
    :return: message json with 200 response
    """
    try:
        etl_timestamp = db.engine.execute("select current_timestamp").fetchone()[0]
    except Exception as tb:
        logging.debug(f"Error during accessing of DB: {traceback.format_exc()}")
        return {"message": f"API is up but Database host {modConfig.dbEtlName} is down."}, 500

    try:
        app_timestamp = db.get_engine(app, modConfig.dbAppName).execute("select current_timestamp").fetchone()[0]
    except Exception as tb:
        logging.debug(f"Error during accessing of DB: {traceback.format_exc()}")
        return {"message": f"API is up but Database host {modConfig.dbAppName} is down."}, 500

    return {"message": f"API and Database are up! Database host {modConfig.dbEtlName} with timestamp: {str(etl_timestamp)} and host {modConfig.dbAppName} with timestamp: {str(app_timestamp)}"}, 200


if __name__ == '__main__':
    import logging
    import multiprocessing_logging

    rootLogger = logging.getLogger()
    rootLogger.setLevel(modConfig.defaultLoggingLevel)
    multiprocessing_logging.install_mp_handler()

    # https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html
    # waitress is lightweight and cross platform
    # performance is not as fast as uwsgi or gunicorn, but still "very acceptable"
    # import requests_mock
    # import requests
    # from modMockResponses import *
    # with requests_mock.Mocker(real_http=True) as mocker:
    #     def match_entity_positively_regulates_entity(request):
    #         trapi = json.loads(request.text)
    #         edges = list(trapi['message']['query_graph']['edges'].keys())
    #         return trapi['message']['query_graph']['edges'][edges[0]]['predicates'][0] == 'biolink:entity_positively_regulates_entity'
    #
    #
    #     def match_coexists_with(request):
    #         trapi = json.loads(request.text)
    #         edges = list(trapi['message']['query_graph']['edges'].keys())
    #         return trapi['message']['query_graph']['edges'][edges[0]]['predicates'][0] == 'biolink:coexists_with'
    #     mocker.register_uri('POST', 'https://arax.ncats.io/api/rtxkg2/v1.2/query', additional_matcher=match_entity_positively_regulates_entity, json=rtx_kg2_entity_positively_regulates_entity)
    #     mocker.register_uri('POST', 'https://arax.ncats.io/api/rtxkg2/v1.2/query', additional_matcher=match_coexists_with, json=rtx_kg2_coexists_with)
    #     mocker.register_uri('POST', 'https://name-resolution-sri.renci.org/lookup', exc=requests.exceptions.ConnectTimeout)
    #     mocker.register_uri('POST', "https://cohd.io/api/query", json=cohd_response)
    if True:
        serve(
            app=TransLogger(
                application=app,
                setup_console_handler=False
            ),
            host=modConfig.host,
            port=modConfig.port,
            threads=modConfig.maxThreadCount
        )
