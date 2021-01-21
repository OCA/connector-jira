"""Odoo CLI command to initiate the Oauth access with Jira

Mostly to be used for the test databases as a wizard does the
same thing from Odoo's UI.

It is plugged in the Odoo CLI commands. The same way "odoo shell"
can be started from the command line, you can use it with the command::

  odoo jiraoauthdance

By default, it will configure the authentication for the Demo Backend
(as it is used in tests). If the demo backend doesn't exist, it will use
the first Jira backend it can find. You can specify a backend ID with::

  odoo jiraoauthdance --backend-id=2

You have to target the database that you want to link, either in the
configuration file, either using the ``--database`` option.

"""

# this is a cli tool, we want to use print statements
# pylint: disable=print-used

import argparse
import logging
import os
import signal
import sys
from contextlib import contextmanager

import odoo
from odoo.cli import Command
from odoo.tools import config

_logger = logging.getLogger(__name__)


def raise_keyboard_interrupt(*a):
    raise KeyboardInterrupt()


class JiraOauthDance(Command):
    def init(self, args):
        config.parse_config(args)
        odoo.cli.server.report_configuration()
        odoo.service.server.start(preload=[], stop=True)
        signal.signal(signal.SIGINT, raise_keyboard_interrupt)

    @contextmanager
    def env(self, dbname):
        with odoo.api.Environment.manage():
            registry = odoo.registry(dbname)
            with registry.cursor() as cr:
                uid = odoo.SUPERUSER_ID
                ctx_environment = odoo.api.Environment(cr, uid, {})["res.users"]
                ctx = ctx_environment.context_get()
                env = odoo.api.Environment(cr, uid, ctx)
                yield env

    def _find_backend(self, env, backend_id=None):
        if backend_id:
            backend = env["jira.backend"].browse(backend_id)
            if not backend.exists():
                die("no backend with id found {}".format(backend_id))
        else:
            backend = env.ref(
                "connector_jira.jira_backend_demo", raise_if_not_found=False
            )
            if not backend:
                backend = self.env["jira.backend"].search([], limit=1)
        return backend

    def oauth_dance(self, dbname, options):
        with self.env(dbname) as env:
            backend = self._find_backend(env, backend_id=options.backend_id)
            auth_wizard = env["jira.backend.auth"].create({"backend_id": backend.id})
            print()
            print(r"Welcome to the Jira Oauth dance \o| \o/ |o/")
            print()
            print(
                "You are working on the backend {} (id: {}) with uri {}".format(
                    backend.name, backend.id, backend.uri
                )
            )
            print(
                "Now, copy the consumer and public key " "in the Jira application link"
            )
            print()
            print("Consumer key:")
            print()
            print(auth_wizard.consumer_key)
            print()
            print("Public key:")
            print()
            print(auth_wizard.public_key)
            print()
            input("Press any key when you have pasted these values in Jira")

            auth_wizard.do_oauth_leg_1()
            print()
            print(
                "Jira wants you to open this link (hostname may change if"
                " you use Docker) and approve the link (no clickbait):"
            )
            print()
            print(auth_wizard.auth_uri)
            print()
            input("Press any key when approved")
            auth_wizard.do_oauth_leg_3()
            print()
            print("That's all folks! Keep these tokens for your tests:")
            print()
            print('JIRA_TEST_URL="{}"'.format(backend.uri))
            print('JIRA_TEST_TOKEN_ACCESS="{}"'.format(backend.access_token))
            print('JIRA_TEST_TOKEN_SECRET="{}"'.format(backend.access_secret))

    def run(self, cmdargs):
        parser = argparse.ArgumentParser(
            prog="%s jiraauthdance" % sys.argv[0].split(os.path.sep)[-1],
            description=self.__doc__,
        )
        parser.add_argument(
            "--backend-id",
            dest="backend_id",
            type=int,
            help="ID of the backend to authenticate. "
            "(by default the demo backend if exists or the first found)",
        )

        args, unknown = parser.parse_known_args(args=cmdargs)

        self.init(unknown)
        if not config["db_name"]:
            die("need a db_name")
        self.oauth_dance(config["db_name"], args)
        return 0


def die(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)
