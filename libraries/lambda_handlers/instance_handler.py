# coding=utf-8

from __future__ import unicode_literals, print_function
import json
from abc import ABCMeta
from libraries.lambda_handlers.handler import Handler
from libraries.tools.lambda_utils import is_lambda_running, set_lambda_running, lambda_min_remaining


class InstanceHandler(Handler):
    """
    Extends the base lambda handler to only allow a single instance
    of the handler to run at any given time.
    """
    __metaclass__ = ABCMeta

    def run(self, **kwargs):
        # check if already running

        self.logger.warning(json.dumps(kwargs))
        event = kwargs['event']
        env_vars = self.retrieve(event, 'stage-variables', 'payload')
        running_db_name = self.retrieve_with_default(env_vars, 'running_db', '{}d43-catalog-running'.format(self.stage_prefix()))

        if is_lambda_running(self.context, running_db_name):
            min_remaining = lambda_min_remaining(self.context)
            self.logger.warning('Lambda started before last execution timed out ({}min). Aborting.'.format(round(min_remaining)))
            return False
        else:
            set_lambda_running(self.context, running_db_name)

        # continue normal execution
        return super(InstanceHandler, self).run(**kwargs)
