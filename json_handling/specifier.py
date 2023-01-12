class Token:
    """
    Token subclass for json_handling class. Specific tokens can be added to the json_handling tuple. Look at the docs for
    the json_handling apply method to see examples of token usage.

    Here is a list of tokens:
    """

    def __init__(self, name, function):
        """
        Create a token. Not meant to be used

        :param name: Name of the token
        :param function: The function the token applies
        This function must take 3 arguments: the token, a json_handling, and an unpacked json
        """
        self.name = name
        self.func = function

    def apply(self, spec, json):
        return self.func(self, spec, json)

    def __repr__(self):
        """
        :return: String representation of the token
        """
        return f"{self.__class__.__name__}.{self.name}"

    @classmethod
    def flatten(cls, lists):
        """
        A list flattener. Takes a nested list and unpacks all the lists
        The result is always a single nested list, even when given something that isn't a list

        :param lists: Any object
        :return: The object with all lists and sublists flattened

        Here is an example of regular flattening
        >>> Token.flatten([[1, 2], [[3], [4]]])
        [1, 2, 3, 4]

        Note not all iterables are flattened, just lists
        >>> Token.flatten([[1, 2], (3, 4)])
        [1, 2, (3, 4)]

        If the object is not a list, it is placed in a list
        >>> Token.flatten(1)
        [1]
        """
        # Add together flattened lists to create flattened list
        return sum([cls.flatten(elt) for elt in lists], start=[]) if type(lists) is list else [lists]

    @staticmethod
    def unpack(lists):
        """
        Flatten two outermost layers into one layer

        :param lists: Any object
        :return: The object with the outer two layers of nested lists flattened

        >>> Token.unpack([[1, 2], [3, 4]])
        [1, 2, 3, 4]

        It doesn't look deeper than a single inner layer
        >>> Token.unpack([[1, 2], [[3], [4]]])
        [1, 2, [3], [4]]

        Like flatten, it doesn't work for non-list iterables
        (More specifically, it doesn't work for any iterables that can't be added to lists)
        However, unlike flatten, if any element of the outer list isn't a list, the unpack fails
        >>> Token.unpack([[1, 2], (3, 4)])
        [[1, 2], (3, 4)]

        Also unlike flatten, if the unpack fails, instead of putting the input in a list, the input is returned directly
        >>> Token.unpack(1)
        1
        """
        try:
            return sum(lists, start=[])
        except TypeError:
            return lists


class Specifier:
    """
    Specifier class to be used with loaded json files to obtain specific data.
    Most of the functionality of the class is in the apply method
    """

    KEEP_ALL = Token(
        'KEEP_ALL',
        lambda self, spec, json: [spec.apply(v) for v in json]
    )
    FLATTEN = Token(
        'FLATTEN',
        lambda self, spec, json: self.flatten(spec.apply(json))
    )
    UNPACK = Token(
        'UNPACK',
        lambda self, spec, json: self.unpack(spec.apply(json))
    )
    tokens = [KEEP_ALL, FLATTEN, UNPACK]

    def __init__(self, specifier_tuple):
        """
        Create a json_handling

        :param specifier_tuple: A tuple containing the keys/tokens for to be applied when using the json_handling
        """
        self.tuple = specifier_tuple

    def __repr__(self):
        """
        :return: String representation of the json_handling, containing the json_handling tuple
        """
        return f"{self.__class__.__name__}({self.tuple})"

    def apply(self, json):
        """
        Apply the json_handling to the argument

        :param json: The json object after being loaded into a python object
        :return: The data obtained from the json object

        Here is an "json" object for testing.
        >>> test_json = {
        ...    "key 1": [
        ...       {
        ...            "key 2": [
        ...                [
        ...                    {
        ...                        "key 3": ["Hello"]
        ...                    },
        ...                    {
        ...                        "key 3": ["There,"]
        ...                    }
        ...                ],
        ...                [
        ...                    {
        ...                        "key 3": ["I"]
        ...                    },
        ...                    {
        ...                        "key 3": ["Have"]
        ...                    },
        ...                    {
        ...                        "key 3": ["Typed"]
        ...                    },
        ...                ]
        ...            ],
        ...            "key 4": 0
        ...        },
        ...        {
        ...            "key 2": [
        ...                [
        ...                    {
        ...                        "key 3": ["Some"]
        ...                    }
        ...                ]
        ...            ],
        ...            "key 4": 1
        ...        },
        ...        {
        ...            "key 2": [
        ...                [
        ...                    {
        ...                        "key 3": ["Text"]
        ...                    }
        ...                ],
        ...                [
        ...                    {
        ...                        "key 3": ["In"]
        ...                    },
        ...                    {
        ...                        "key 3": ["Json"]
        ...                    }
        ...                ]
        ...            ],
        ...            "key 4": 2
        ...        }
        ...    ],
        ...    "key 5": 3
        ... }

        Getting one specific thing from a json
        >>> Specifier(("key 1", 0, "key 2", 0, 0, "key 3", 0)).apply(test_json)
        'Hello'

        Getting multiple things in nested list
        >>> Specifier(("key 1", "key 2", "key 3")).apply(test_json)
        [[[['Hello'], ['There,']], [['I'], ['Have'], ['Typed']]], [[['Some']]], [[['Text']], [['In'], ['Json']]]]

        Getting multiple things in nested list with indices
        >>> Specifier(("key 1", 0, "key 2", "key 3")).apply(test_json)
        [[['Hello'], ['There,']], [['I'], ['Have'], ['Typed']]]

        Note that only the first thing in the array indexed by "key 1" was obtained because of the index

        Getting multiple things in flattened list
        >>> Specifier((Specifier.FLATTEN, "key 1", "key 2", "key 3")).apply(test_json)
        ['Hello', 'There,', 'I', 'Have', 'Typed', 'Some', 'Text', 'In', 'Json']

        Getting multiple things in flattened list with index
        >>> Specifier((Specifier.FLATTEN, "key 1", 0, "key 2", "key 3")).apply(test_json)
        ['Hello', 'There,', 'I', 'Have', 'Typed']

        More info about FLATTEN
        In this example, the sequence of keys and lists can be thought of as this:
        key 1, [, key 2, [, [, key 3, [
        Placing a FLATTEN after a key will take all the nesting after it and turn it into a flat list:
        FLATTEN, key 1, key 2, key 3
        Can be thought of as
        FLATTEN, key 1, [, key 2, [, [, key 3, [
        And the FLATTEN removes all the nesting because all of it occurs to the right of flatten
        This is also true for this json_handling:
        key 1, FLATTEN, [, key 2, [, [, key 3, [
        However, in this example we place the flatten after key 2:
        key 1, [, key 2, FLATTEN, [, [, key 3, [
        Since there is still a list before the FLATTEN, the result will be double nested.
        >>> Specifier(("key 1", "key 2", Specifier.FLATTEN, "key 3")).apply(test_json)
        [['Hello', 'There,', 'I', 'Have', 'Typed'], ['Some'], ['Text', 'In', 'Json']]

        If you want to place the FLATTEN between two [, then use the KEEP_ALL token
        key 1, key 2, KEEP_ALL, FLATTEN, key 3
        becomes
        key 1, [, key 2, [, FLATTEN, [, key 3, [
        So the result is triple nested because the flatten takes the two [ on the right and turns them into 1
        >>> Specifier(("key 1", "key 2", Specifier.KEEP_ALL, Specifier.FLATTEN, "key 3")).apply(test_json)
        [[['Hello', 'There,'], ['I', 'Have', 'Typed']], [['Some']], [['Text'], ['In', 'Json']]]

        Using single UNPACK at start
        >>> Specifier((Specifier.UNPACK, "key 1", "key 2", "key 3")).apply(test_json)
        [[['Hello'], ['There,']], [['I'], ['Have'], ['Typed']], [['Some']], [['Text']], [['In'], ['Json']]]

        More info about UNPACK:
        UNPACK is similar to FLATTEN, but instead of removing all nesting to the right, it combines the two closest
        layers to its right
        This example is this:
        key 1, [, key 2, UNPACK, [, [, key 3, [
        >>> Specifier(("key 1", "key 2", Specifier.UNPACK, "key 3")).apply(test_json)
        [[['Hello'], ['There,'], ['I'], ['Have'], ['Typed']], [['Some']], [['Text'], ['In'], ['Json']]]

        The KEEP_ALL token will delay the use of the next token if the next token has to do with lists
        In this example, the index 0 is not applied to the list obtained by applying "key 2", but the sublist within
        that list. In other words, the KEEP_ALL token will leave a specific layer of nesting untouched
        Getting multiple things in nested list with index after KEEP_ALL
        >>> Specifier(("key 1", "key 2", Specifier.KEEP_ALL, 0, "key 3")).apply(test_json)
        [[['Hello'], ['I']], [['Some']], [['Text'], ['In']]]

        Getting multiple things in flattened list with index after KEEP_ALL
        >>> Specifier((Specifier.FLATTEN, "key 1", "key 2", Specifier.KEEP_ALL, 0, "key 3")).apply(test_json)
        ['Hello', 'I', 'Some', 'Text', 'In']

        KEEP_ALL being used to delay an UNPACK. This is a representation of the pipeline:
        key 1, [, key 2, [, UNPACK, [, key 3, [
        >>> Specifier(("key 1", "key 2", Specifier.KEEP_ALL, Specifier.UNPACK, "key 3")).apply(test_json)
        [[['Hello', 'There,'], ['I', 'Have', 'Typed']], [['Some']], [['Text'], ['In', 'Json']]]
        """
        if not self.tuple:  # An empty json_handling leaves the json unchanged
            return json

        name, *rest = self.tuple

        if name in self.tokens:
            # If it's a token, apply the token with a json_handling for the remaining names in the tuple
            other_spec = self.__class__(rest)
            json = name.apply(other_spec, json)
        else:
            # This is what happens to regular keys
            success = True
            try:
                # First, a regular indexing is tried
                json = json[name]
            except TypeError:
                # If the regular indexing fails, it should be because a string index was applied to a list
                success = False

            if success:
                # If the key was successfully applied, just apply the rest of the json_handling if there is any
                if rest:
                    other_spec = self.__class__(rest)
                    json = other_spec.apply(json)
            else:
                # If json is a list, then apply the json_handling to each thing in the list
                other_spec = self.__class__(self.tuple)
                json = [other_spec.apply(v) for v in json]

        return json


if __name__ == '__main__':
    import doctest
    doctest.testmod()
