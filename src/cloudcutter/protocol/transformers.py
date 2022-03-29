from typing import List, Dict, Union, Set

class ResponseTransformer(object):
    def __init__(self, keys: Set[str], reworking_function):
        self.reworking_function = reworking_function
        self.keys = keys

    def apply(self, response: Union[List,Dict]):
        if isinstance(response, List):
            return self.__recurse_apply_list(response)
        else:
            return self.__recurse_apply_dict(response)

    def __recurse_apply_list(self, response: List):
        new_response = []
        for v in response:
            if isinstance(v, Dict):
                new_response.append(self.__recurse_apply_dict(v))
            elif isinstance(v, List):
                new_response.append(self.__recurse_apply_list(v))
            else:
                new_response.append(v)
        return new_response

    def __recurse_apply_dict(self, response: Dict):
        new_response = {}
        for k, v in response.items():
            if isinstance(v, List):
                new_response[k] = self.__recurse_apply_list(v)
            elif isinstance(v, Dict):
                new_response[k] = self.__recurse_apply_dict(v)
            else:
                new_response[k] = v
                if k in self.keys:
                    new_response[k] = self.reworking_function(v)
        return new_response