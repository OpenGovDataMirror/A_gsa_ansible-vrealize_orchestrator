#!/usr/bin/python
from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'metadata_version': '1.1'}
try:
    import json
    import time
    from urlparse import urlparse
    from ansible.module_utils.basic import AnsibleModule
    from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
    from ansible.module_utils.urls import open_url
    from ansible.module_utils.urls import ConnectionError, SSLValidationError
    HAS_LIB = True
except ImportError:
    HAS_LIB = False


class VROClient(object):
    """
    vRO config
    """

    BASE_URL = "https://{}:{}/vco/{}"

    def __init__(self, module):
        self.module = module
        self.user = self.module.params['username']
        self.pwd = self.module.params['password']
        self.server = self.module.params['hostname']
        self.port = self.module.params['port']
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}
        self.validate_certs = self.module.params['validate_certs']
        self.inputs = self.module.params['inputs']

    def _api_url(self, path):
        api_url_template = "api/{}"
        api_path = api_url_template.format(path)
        return self.BASE_URL.format(self.server, self.port, api_path)

    def _fail(self, msg):
        fail_msg = "Message: {}".format(msg)
        self.module.fail_json(msg=fail_msg)

    def _do_send(self, method, path, data=None):

        url = self._api_url(path)

        resp = None
        if data is None and method == 'POST':
            data = "{}"

        try:
            resp = open_url(
                url, headers=self.headers,
                url_username=self.user, url_password=self.pwd,
                validate_certs=self.validate_certs,
                method=method, force_basic_auth=True,
                data=data)
        except HTTPError as err:
            self._fail("Received HTTP error: %s" % (str(err)))
        except URLError as err:
            self._fail("Failed lookup url: %s" % (str(err)))
        except SSLValidationError as err:
            self._fail("Error validating the server's certificate: %s" % (str(err)))
        except ConnectionError as err:
            self._fail("Error connecting: %s" % (str(err)))

        raw_data = resp.read()
        status_code = resp.getcode()
        status_url = resp.geturl()
        status_info = resp.info()

        try:
            if raw_data:
                data = json.loads(raw_data)
            else:
                data = None
        except TypeError:
            fail_msg = "Unable to convert to JSON"
            self._fail(fail_msg)

        return status_code, status_url, status_info, data

    def _do_get(self, path, data=None):
        return self._do_send('GET', path, data)

    def _do_post(self, path, data=None):
        return self._do_send('POST', path, data)

    def workflow_id(self, wf_name):

        path = 'workflows?conditions=name={}'.format(wf_name)
        wf_href = None

        status_code, status_url, status_info, data = self._do_get(path)

        if data:
            wf_count = data['total']
        else:
            wf_count = 0

        if wf_count == 0:
            self._fail("Could not find workflow: {}".format(wf_name))
        elif wf_count > 1:
            self._fail("Cannot determine uniqueness.  "
                       "Found {} instances of workflow: {}.".format(wf_count, wf_name))

        for i in data['link']:
            wf_href = [x['value'] for x in i['attributes'] if x['name'] == 'id'][0]

        return wf_href

    def run_workflow(self, workflow_id, inputs):

        path = "workflows/{}/executions/".format(workflow_id)

        if inputs:
            try:
                json_data = json.dumps(inputs)
            except TypeError:
                fail_msg = "Invalid inputs.  Unable to convert to JSON"
                self._fail(fail_msg)
        else:
            json_data = None

        status_code, status_url, status_info, data = self._do_post(path, json_data)

        if status_code != 202:
            fail_msg = "POST failed with status code: {}".format(status_code)
            self._fail(fail_msg)

        url = status_info['location']
        execution_id = urlparse(url).path.split('/')[-2]

        return execution_id

    def run_workflow_state(self, workflow_id, execution_id):

        path = "workflows/{}/executions/{}/state".format(workflow_id, execution_id)

        status_code, status_url, status_info, data = self._do_get(path)

        if status_code != 200:
            fail_msg = "Failed to get state workflow: {} " \
                       "execution id: {}".format(workflow_id, execution_id)
            self._fail(fail_msg)

        return data['value']

    def run_workflow_result(self, workflow_id, execution_id):

        path = "workflows/{}/executions/{}/".format(workflow_id, execution_id)

        status_code, status_url, status_info, data = self._do_get(path)

        if status_code != 200:
            fail_msg = "Failed to get state workflow: {} " \
                       "execution id: {}".format(workflow_id, execution_id)
            self._fail(fail_msg)

        return data

    def wait_for_workflow(self, workflow_id, execution_id, timeout, sleep=2):

        start = time.time()
        timeout_exceded = False

        while not timeout_exceded:
            workflow_state = self.run_workflow_state(workflow_id, execution_id)

            if workflow_state in ('failed', 'completed', 'canceled'):
                return workflow_state

            else:
                time.sleep(sleep)

            current = time.time()

            if (current - start) >= timeout:
                return 'timeout'

    def get_wf_run_status(self, workflow_id):

        path = "workflows/{}/executions/".format(workflow_id)

        status_code, status_url, status_info, data = self._do_get(path)

        if status_code != 200:
            self._fail("Failed getting runs for workflow: "
                       "id: {}".format(workflow_id))

        content = json.loads(data)
        total = content['relations']['total']

        if not total >= 1:
            self._fail("No runs found for id: {} total: {}"
                       .format(workflow_id, total))

        wfruns = [i[x] for i in content['relations']['link'] for x in i.iterkeys() if x == 'attributes']

        failed_wfs = []

        for wfrun in wfruns:
            wfdata = {}
            for i in wfrun:
                for key in i.iterkeys():
                    if i[key] in ('state', 'id', 'endDate'):
                        wfdata.update({i[key]: i['value']})

            if wfdata['state'] == 'failed':
                failed_wfs.append(wfdata['id'])

        return failed_wfs


def main():
    argument_spec = dict(
        hostname=dict(required=True, type='str'),
        port=dict(required=False, type='str', default='443'),
        username=dict(required=True, type='str'),
        password=dict(required=True, type='str', no_log=True),
        name=dict(required=False, type='str'),
        uuid=dict(required=False, type='str'),
        inputs=dict(required=False, type='dict'),
        state=dict(type='str', default='started',
                   choices=['started']),
        timeout=dict(required=False, type='int', default=600),
        validate_certs=dict(required=False, type='bool', default=True),
        wait_for_workflow=dict(required=False, type='bool', default=True)
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=False,
                           required_one_of=[['name', 'uuid']])

    if not HAS_LIB:
        module.fail_json(msg='python modules failed \
                              to import required for this module')

    vro = VROClient(module)

    if module.params['state'] == 'started':
        workflow_name = module.params['name']
        timeout_value = module.params['timeout']
        workflow_id = module.params['uuid']
        inp = module.params['inputs']
        wait_workflow = module.params['wait_for_workflow']

        if workflow_name:
            workflow_id = vro.workflow_id(workflow_name)

        execution_id = vro.run_workflow(workflow_id, inp)

        if wait_workflow:
            wf_status = vro.wait_for_workflow(workflow_id, execution_id,
                                              timeout_value)

            if wf_status == 'completed':
                wf_result = vro.run_workflow_result(workflow_id, execution_id)
                module.exit_json(changed=True, execution_id=execution_id,
                                 status=wf_status, result=wf_result)
            else:
                module.fail_json(msg="Workflow status: {}".format(wf_status),
                                 execution_id=execution_id, status=wf_status)
        else:
            module.exit_json(changed=True, execution_id=execution_id)


if __name__ == '__main__':
    main()
