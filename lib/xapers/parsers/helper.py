import subprocess


def call_cmd(cmdlist, stdin=None):
    """
    get a shell commands output, error message and return value and immediately
    return.

    :param cmdlist: shellcommand to call, already splitted into a list accepted
                    by :meth:`subprocess.Popen`
    :type cmdlist: list of str
    :param stdin: string to pipe to the process
    :type stdin: str
    :return: triple of stdout, error msg, return value of the shell command
    :rtype: str, str, int
    """

    out, err, ret = '', '', 0
    try:
        if stdin:
            proc = subprocess.Popen(cmdlist, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            out, err = proc.communicate(stdin)
            ret = proc.poll()
        else:
            out = subprocess.check_output(cmdlist)
            # todo: get error msg. rval
    except (subprocess.CalledProcessError, OSError), e:
        err = str(e)
        ret = -1

    return out, err, ret
