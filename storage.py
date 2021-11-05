# -*- coding:utf-8 -*-

import json
import logging
import collections
import utils
import constants as const


class Storage(object):
    """
    数据存储类
    """
    def __init__(self, path):
        self.path = path
        self.data = collections.OrderedDict()

    def loadData(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data = collections.OrderedDict(json.loads(f.read()))
                # return collections.OrderedDict(json.loads(f.read(), object_hook=collections.OrderedDict))
        except Exception as e:
            logging.exception(e)
        return self.data

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(utils.objectToJsonStr(self.data))

    def getData(self):
        return self.data

    def loggingData(self):
        logging.info("Storage data: {}".format(utils.objectToJsonStr(self.getData())))

    def updateProjectName(self, old, new):
        if old != new:
            if new in self.data:
                return False
            if old in self.data:
                self.data[new] = self.data[old]
                del self.data[old]
                self.save()
        return True

    def updateServiceName(self, project, old, new):
        if old != new:
            try:
                if new in self.data[project]:
                    return False
                self.data[project][new] = self.data[project][old]
                del self.data[project][old]
                self.save()
            except Exception as e:
                logging.exception(e)
                return False
        return True

    def updateModuleName(self, project, service, old, new):
        if old != new:
            try:
                if new in self.data[project][service]:
                    return False
                self.data[project][service][new] = self.data[project][service][old]
                del self.data[project][service][old]
                self.save()
            except Exception as e:
                logging.exception(e)
                return False
        return True

    def updateMethodName(self, project, service, module, old, new):
        if old != new:
            try:
                if new in self.data[project][service][module]:
                    return False
                self.data[project][service][module][new] = self.data[project][service][module][old]
                del self.data[project][service][module][old]
                self.save()
            except Exception as e:
                logging.exception(e)
                return False
        return True

    def _has_method(self, project, service, module, method):
        return (
                project in self.data
                and service in self.data[project]
                and module in self.data[project][service]
                and method in self.data[project][service][module]
        )

    def updateParams(self, project, service, module, method, params):
        if self._has_method(project, service, module, method):
            self.data[project][service][module][method][const.PARAMS] = params if isinstance(params, dict) else dict()
            # self.data[service][module][method][CONST_RESULT] = result if isinstance(result, dict) else dict()
            self.save()

    def updateResut(self, project, service, module, method, result):
        if self._has_method(project, service, module, method):
            if isinstance(result, list) or isinstance(result, dict):
                self.data[project][service][module][method][const.RESULT] = result
                self.save()

    def addProject(self, project):
        if project in self.data:
            return False
        self.data[project] = dict()
        self.save()
        return True

    def addService(self, project, service):
        if service in self.data[project]:
            return False
        self.data[project][service] = dict()
        self.save()
        return True

    def addModule(self, project, service, module):
        if project in self.data and service in self.data[project] and module in self.data[project][service]:
            return False
        self.data[project][service][module] = dict()
        self.save()
        return True

    def _convert_params(self, params):
        data = {const.PARAMS: dict(), const.RESULT: dict()}
        if params:
            data[const.PARAMS] = params
        return data

    def addMethod(self, project, service, module, method, params):
        if self._has_method(project, service, module, method):
            return False
        self.data[project][service][module][method] = self._convert_params(params)
        self.save()
        return True

    def deleteMethod(self, project, service, module, method):
        if self._has_method(project, service, module, method):
            del self.data[project][service][module][method]
            self.save()

    def getParam(self, project, service, module, method):
        try:
            return self.data[project][service][module][method][const.PARAMS]
        except Exception as e:
            logging.exception(e)
            return collections.OrderedDict()

    def getResult(self, project, service, module, method):
        try:
            return self.data[project][service][module][method][const.RESULT]
        except Exception as e:
            logging.exception(e)
            return collections.OrderedDict()
