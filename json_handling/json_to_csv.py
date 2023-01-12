from json_handling import Specifier
from itertools import chain
import csv
import io


class JsonProcessor:
    """
    A class that wraps loaded jsons
    """
    def __init__(self, json):
        """
        :param json: A json that has been loaded
        """
        self.json = json

    def __getitem__(self, specifier):
        """
        Indexing can be used with a JsonProcessor to extract data using a json_handling
        The data obtained is wrapped in a JsonProcessor before being returned
        This allows for multiple specifiers to be applied with multiple indexing
        For more info, look at the docs for Specifier.apply

        :param specifier: A Specifier
        :return: Another JsonProcessor object, but containing the extracted data
        """
        return self.__class__(specifier.apply(self.json))

    # TODO: Maybe think about better way for index column?
    def make_csv(self, column_specifiers, context_specifier=Specifier(()), take_product=False):
        """
        Makes a csv from the json data

        :param column_specifiers: A map from column names to specifiers for obtaining the column data
        :param context_specifier: A json_handling to apply before applying the other specifiers
        :param take_product: Whether or not to apply a cartesian product if some column data is nested
        :return: csv-formatted string

        >>> test_json = JsonProcessor([
        ...     {
        ...         'id': 0,
        ...         'points': [
        ...             {
        ...                 'id': 0,
        ...                 'data': [1, 2, 3]
        ...             },
        ...             {
        ...                 'id': 2,
        ...                 'data': [9, 8, 7]
        ...             }
        ...         ],
        ...         'name': 'line 1',
        ...         'desc': 'This is a line segment'
        ...     },
        ...     {
        ...         'id': 1,
        ...         'points': [
        ...             {
        ...                 'id': 1,
        ...                 'data': [1, 2, 3]
        ...             }
        ...         ],
        ...         'name': 'point 1',
        ...         'desc': 'This is a single point'
        ...     },
        ... ])

        Creating a dataframe:
        >>> test_json.make_csv(
        ...     {
        ...         'id': Specifier(('id',)),
        ...         'name': Specifier(('name',)),
        ...         'description': Specifier(('desc',))
        ...     }
        ... )
        'id,name,description\\r\\n0,line 1,This is a line segment\\r\\n1,point 1,This is a single point\\r\\n'

        Note that the index name is index by default when an index json_handling is provided
        A by-product of this is that 'index' is not allowed as a column name

        We can use the context json_handling to get a dataframe of the points
        >>> test_json.make_csv(
        ...     {
        ...         'id': Specifier(('id',)),
        ...         'data': Specifier(('data',)),
        ...     },
        ...     context_specifier=Specifier((Specifier.FLATTEN, 'points'))
        ... )
        'id,data\\r\\n0,"[1, 2, 3]"\\r\\n2,"[9, 8, 7]"\\r\\n1,"[1, 2, 3]"\\r\\n'

        We can also put indices in the json_handling to unpack the shape dimensions in this example a little better
        >>> test_json.make_csv(
        ...     {
        ...         'id': Specifier(('id',)),
        ...         'dim1': Specifier(('data', 0)),
        ...         'dim2': Specifier(('data', 1)),
        ...         'dim3': Specifier(('data', 2)),
        ...     },
        ...     context_specifier=Specifier((Specifier.FLATTEN, 'points'))
        ... )
        'id,dim1,dim2,dim3\\r\\n0,1,2,3\\r\\n2,9,8,7\\r\\n1,1,2,3\\r\\n'

        The take_product argument is great for creating relation tables.
        Here is an example without the take_product
        >>> test_json.make_csv(
        ...     {
        ...         'shape_id': Specifier(('id',)),
        ...         'point_id': Specifier(('points', 'id'))
        ...     }
        ... )
        'shape_id,point_id\\r\\n0,"[0, 2]"\\r\\n1,[1]\\r\\n'

        Here is an example of creating a relation table with take_product=True
        >>> test_json.make_csv(
        ...     {
        ...         'shape_id': Specifier(('id',)),
        ...         'point_id': Specifier(('points', 'id'))
        ...     },
        ...     take_product=True
        ... )
        'shape_id,point_id\\r\\n0,0\\r\\n0,2\\r\\n1,1\\r\\n'
        """

        # Apply context
        w_context = self[context_specifier]

        # Handle column specifiers
        column_specifiers = {**column_specifiers}  # In case it's not a dictionary

        # Obtain column data
        column_data = {
            column_name: w_context[column_specifier].json
            for column_name, column_specifier in column_specifiers.items()
        }

        columns = list(column_data.values())
        rows = zip(*columns)

        if take_product:
            # Take cartesian product of columns
            # Perform the cartesian product
            rows = chain(*(self.conditional_product(row, key=lambda v: isinstance(v, list)) for row in rows))

        with io.StringIO(newline='') as csvstream:
            writer = csv.writer(csvstream)
            writer.writerow(column_data.keys())
            writer.writerows(rows)

            return csvstream.getvalue()

    @classmethod
    def conditional_product(cls, vals, key=None):
        """
        Performs a cartesian product, but only expanding some of the values

        :param vals: The values to create products over
        :param key: Which values should be used for the product. Can be key value, function, or iterable
        :return: An iterable of tuples with the products

        It can be used for regular cartesian products
        >>> list(JsonProcessor.conditional_product([(1, 2), (3, 4), (6, 7)]))
        [(1, 3, 6), (1, 3, 7), (1, 4, 6), (1, 4, 7), (2, 3, 6), (2, 3, 7), (2, 4, 6), (2, 4, 7)]

        If some things are not iterable, then they are ignored in the cartesian product
        >>> list(JsonProcessor.conditional_product([(1, 2), 2.5, (3, 4), 4.5]))
        [(1, 2.5, 3, 4.5), (1, 2.5, 4, 4.5), (2, 2.5, 3, 4.5), (2, 2.5, 4, 4.5)]

        A key can be provided to specify which specific iterables to expand.
        This key can be a mask or a predicate function.
        Mask example:
        >>> list(JsonProcessor.conditional_product([(1, 2), (3, 4)], key=[True, False]))
        [(1, (3, 4)), (2, (3, 4))]

        Predicate function example:
        >>> list(JsonProcessor.conditional_product([(1, 2), (3, 4, 5), (6, 7)], key=lambda val: len(val) % 2))
        [((1, 2), 3, (6, 7)), ((1, 2), 4, (6, 7)), ((1, 2), 5, (6, 7))]
        """

        # By default, expand all iterables
        if key is None:
            key = cls.isiterable

        if callable(key):
            # Turn key to iterable then recurse
            return cls.conditional_product(vals, map(key, vals))
        elif cls.isiterable(key):
            return cls._curr_gen(vals, key)
        else:
            raise ValueError("Key must either be a predicate function or a mask iterable")

    @staticmethod
    def _curr_gen(vals, key):
        """
        A helper function for conditional_predicate

        :param vals: A collection of values
        :param key: A mask for which to expand in the product
        :return: An iterable over the tuples in the product
        """
        key = tuple(key)
        # Make list of iters (and values)
        iters = [iter(val) if pred else val for pred, val in zip(key, vals)]
        # Curr will be updated to make elements of the product
        curr = [next(it) if pred else it for pred, it in zip(key, iters)]
        while True:
            yield tuple(curr)
            # Loop through iterables backwards
            for pred, idx in zip(reversed(key), range(len(vals)-1, -1, -1)):
                if not pred:
                    # Skip over the ones to not expand
                    continue

                try:
                    # Try getting the next thing
                    curr[idx] = next(iters[idx])
                    break
                except StopIteration:
                    # If there is no next thing, reset this iterable and try the previous one
                    iters[idx] = iter(vals[idx])
                    curr[idx] = next(iters[idx])
            else:
                # If all the iterators are exhausted, then no break occured
                # In this case, we are finished iterating
                break

    @staticmethod
    def isiterable(val):
        """
        Check if something is iterable

        :param val: The value to check
        :return: True if it is iterable, otherwise false
        """
        iterable = False
        try:
            iter(val)
            iterable = True
        except TypeError:
            pass
        return iterable


if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
