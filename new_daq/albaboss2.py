import argparse
import subprocess
import datetime
import yaml
import time
import logging
import threading
import os

# ----------------------------------------------------------------------------------------------------------------------------
class ThreadedSubprocess(threading.Thread):
    def __init__(self, cmd, retries, sleep):
        self.cmd = cmd
        self.retries = retries
        self.sleep = sleep
        threading.Thread.__init__(self)
        self.daemon = True
        self.name = cmd

    def run(self):
        for tries in range(1, self.retries+1):
            self.process = subprocess.Popen(self.cmd.split())
            logger.info("Command '{}' started on try {} of {} with pid {}".format(self.cmd, tries, retries, self.process.pid))
            self.process.wait()
            if self.process.returncode == 0:
                logger.info("Command '{}' with pid {} ended on try {} of {} with return code {}".format(self.cmd, self.process.pid, tries, retries, self.process.returncode))
                break
            elif self.process.returncode == -15:
                logger.warning("Command '{}' with pid {} was sent SIGTERM signal".format(self.cmd, self.process.pid))
                break
            elif self.process.returncode == -9:
                logger.warning("Command '{}' with pid {} was sent SIGKILL signal".format(self.cmd, self.process.pid))
                break
            else:
                logger.error("Command '{}' with pid {} failed on try {} of {} with return code {}".format(self.cmd, self.process.pid, tries, retries, self.process.returncode))
            if self.sleep > 0:
                time.sleep(self.sleep)
                    
    def terminate(self):
        """ Send SIGTERM(15) signal to the current process """
        self.process.terminate()
# ----------------------------------------------------------------------------------------------------------------------------
def terminate_running_threads(threads):
    """ Terminate all running threads """
    for thread in threads:
        thread.terminate()
        time.sleep(0.1)
# ----------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument("configfile", help="yaml file containing albaboss configuration parameters")
    args=parser.parse_args()

    parameters=None

    with open(args.configfile, 'r') as cf:
        parameters=yaml.load(cf.read())
        
    logger = logging.getLogger()
    logger.setLevel(parameters["logging"]["level"])
    log_formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s", "%d-%m-%Y %H:%M:%S")
    if parameters["logging"]["directory"] == "None":
        log_handler = logging.StreamHandler()
    else:
        if not os.path.isdir(parameters["logging"]["directory"]):
            os.makedirs(parameters["logging"]["directory"])
        log_handler = logging.FileHandler(parameters["logging"]["directory"]+"/albaboss/"+datetime.datetime.now().strftime("%d%m%Y_%H%M%S")+".log")
    log_handler.setFormatter(log_formatter)
    log_handler.setLevel(parameters["logging"]["level"])
    logger.addHandler(log_handler)

    logger.info("Starting albaboss")

    parallel_threads = []
    
    for process_type in ["serial-processes", "parallel-processes"]:
        logger.info("Running {}".format(process_type))
        processes_keys = parameters[process_type].keys()
        processes_keys.sort()
        for process in processes_keys:
            cmd = parameters[process_type][process]["cmd"]
            retries = parameters[process_type][process]["retries"]
            sleep = parameters[process_type][process]["sleep"]

            thread = ThreadedSubprocess(cmd, retries, sleep)
            thread.start()

            time.sleep(0.1)

            if process_type == "serial-processes":
                thread.join()
                if thread.process.returncode != 0:
                    logger.error("Command '{}' has ended unexpectedly. Exiting albaboss with return code 1".format(cmd))
                    exit(1)
            else:
                parallel_threads.append(thread)

    while len(parallel_threads) != 0:
        for n, thread in enumerate(parallel_threads):
            if thread.is_alive():
                pass
            else:
                if thread.process.returncode == 0:
                    logger.info("Command '{}' has ended successfully".format(thread.cmd))
                    parallel_threads.pop(n)
                elif thread.process.returncode == -9 or thread.process.returncode == -15:
                    logger.info("Command '{}' was killed/terminated by user".format(thread.cmd))
                    parallel_threads.pop(n)
                else:
                    logger.critical("Command '{}' has ended unexpectedly".format(thread.cmd))
                    parallel_threads.pop(n)
                    logger.info("Looking for active threads")
                    if len(parallel_threads) > 0:
                        logger.info("Found {} active threads. Terminating them now.".format(len(parallel_threads)))
                        terminate_running_threads(parallel_threads)
                    else:
                        logger.info("Found 0 active threads")
                    logger.critical("Exiting albaboss with return code 1")
                    exit(1)
        time.sleep(0.1)
                    
    exit(0)                    
   
