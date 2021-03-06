# Copyright 2014, Sandia Corporation. Under the terms of Contract
# DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
# rights in this software.

from __future__ import division

import collections
import itertools
import numbers
import numpy
import sys
import toyplot.color
import toyplot.compatibility
import xml.etree.ElementTree as xml

try:
    import pandas
except: # pragma: no cover
    pass


def contiguous(a):
    """Split an array into a collection of contiguous ranges.
    """
    i = 0
    begin = []
    end = []
    values = []
    for (value, group) in itertools.groupby(numpy.array(a).ravel()):
        begin.append(i)
        end.append(i + len(list(group)))
        values.append(value)
        i = end[-1]
    return numpy.array(begin), numpy.array(end), numpy.array(values)


class Table(object):
    """Encapsulates an ordered, heterogeneous collection of labelled data series.

    Parameters
    ----------
    data: (data series, optional)
        You may initialize a toyplot.data.Table with any of the following:

        * None (the default) - creates an empty table (a table without any columns).
        * :class:`toyplot.data.Table` - creates a copy of the given table.
        * :class:`collections.OrderedDict` - creates a column for each key-value pair in the input, in the same order.  Each value must be implicitly convertable to a numpy masked array, and every value must contain the same number of items.
        * object returned when loading a `.npz` file with :func:`numpy.load` - creates a column for each key-value pair in the given file, in the same order.  Each array in the input file must contain the same number of items.
        * :class:`dict` / :class:`collections.Mapping` - creates a column for each key-value pair in the input, sorted by key in lexicographical order.  Each value must be implicitly convertable to a numpy masked array, and every value must contain the same number of items.
        * :class:`list` / :class:`collections.Sequence` - creates a column for each key-value tuple in the input sequence, in the same order.  Each value must be implicitly convertable to a numpy masked array, and every value must contain the same number of items.
        * :class:`numpy.ndarray` - creates a column for each column in a numpy matrix (2D array).  The order of the columns is maintained, and each column is assigned a unique name.
        * :class:`pandas.core.frame.DataFrame` - creates a column for each column in a `Pandas <http://pandas.pydata.org>`_ data frame.  The order of the columns is maintained.

    index: bool or string, optional
        Controls whether to convert a `Pandas <http://pandas.pydata.org>`_ data
        frame index to columns in the resulting table.  Use index=False (the
        default) to leave the data frame index out of the table.  Use
        index=True to include the index in the table, using default column
        names (hierarchical indices will be stored in the table using multiple
        columns).  Use index="format string" to include the index and control
        how the index column names are generated.  The given format string can
        use positional `{}` / `{0}` or keyword `{index}` arguments to
        incorporate a zero-based index id into the column names.
    """

    def __init__(self, data=None, index=False):
        self._columns = collections.OrderedDict()
        self._metadata = collections.defaultdict(dict)

        if data is not None:
            keys = None
            values = None

            # Input data for which an explicit column ordering is known.
            if isinstance(data, (
                    collections.OrderedDict,
                    toyplot.data.Table,
                    numpy.lib.npyio.NpzFile,
                )):
                keys = [key for key in data.keys()]
                values = [data[key] for key in keys]
            # Input data for which an explicit column ordering is not known.
            elif isinstance(data, (dict, collections.Mapping)):
                keys = [key for key in sorted(data.keys())]
                values = [data[key] for key in keys]
            # Input data based on sequences.
            elif isinstance(data, (list, collections.Sequence)):
                keys = [key for key, value in data]
                values = [value for key, value in data]
            # Input data based on numpy arrays.
            elif isinstance(data, numpy.ndarray):
                if data.ndim != 2:
                    raise ValueError(
                        "Only two-dimensional arrays are allowed.")
                keys = [str(i) for i in numpy.arange(data.shape[1])]
                values = [data[:, i] for i in numpy.arange(data.shape[1])]
            # Input data based on Pandas data structures.
            elif "pandas" in sys.modules and isinstance(data, pandas.DataFrame):
                    keys = [str(data.ix[:,i].name) for i in range(data.shape[1])]
                    values = [data.ix[:,i] for i in range(data.shape[1])]

                    if index:
                        key_format = "index{}" if index == True else index
                        keys = [key_format.format(i, index=i) for i in range(data.index.nlevels)] + keys
                        values = [data.index.get_level_values(i) for i in range(data.index.nlevels)] + values
            else:
                raise ValueError("Can't create a toyplot.data.Table from an instance of %s" % type(data))

            # Get the set of unique keys, so we can see if there are any duplicates.
            keys = numpy.array(keys, dtype="object")
            key_dictionary, key_counts = numpy.unique(keys, return_counts=True)

            if numpy.any(key_counts > 1):
                toyplot.log.warn("Altering duplicate column names to make them unique.")

            # "Reserve" all of the keys that aren't duplicated.
            reserved_keys = set([key for key, count in zip(key_dictionary, key_counts) if count == 1])
            # Now, iterate through the keys that do contain duplicates, altering them to make them unique,
            # while ensuring that the unique versions don't conflict with reserved keys.
            for key, count in zip(key_dictionary, key_counts):
                if count == 1:
                    continue

                suffix = 1
                for i in numpy.flatnonzero(keys == key):
                    if key not in reserved_keys:
                        reserved_keys.add(key)
                        continue
                    while "%s-%s" % (key, suffix) in reserved_keys:
                        suffix += 1
                    keys[i] = "%s-%s" % (key, suffix)
                    reserved_keys.add(keys[i])

            # Store the data.
            for key, value in zip(keys, values):
                self[key] = value


    def __getitem__(self, index):
        column = None
        column_slice = None

        # Cases that return a column (array):

        # table["a"]
        if isinstance(index, toyplot.compatibility.string_type):
            column = index
            column_slice = slice(None, None, None)
        elif isinstance(index, tuple) and isinstance(index[0], toyplot.compatibility.string_type):
            column = index[0]
            # table["a", 10]
            if isinstance(index[1], numbers.Integral):
                column_slice = slice(index[1], index[1] + 1)
            # table["a", 10:20], table["a", [10, 12, 18]], etc.
            else:
                column_slice = index[1]

        if column is not None and column_slice is not None:
            return self._columns[column][column_slice]

        row_slice = None
        columns = None

        # table[10]
        if isinstance(index, numbers.Integral):
            row_slice = slice(index, index + 1)
            columns = self._columns.keys()
        # table[10:20]
        elif isinstance(index, slice):
            row_slice = index
            columns = self._columns.keys()
        elif isinstance(index, tuple):
            # table[10, ]
            if isinstance(index[0], numbers.Integral):
                row_slice = slice(index[0], index[0] + 1)
            # table[10:20, ], table[[10, 12, 18], ], etc.
            else:
                row_slice = index[0]

            # table[, "a"]
            if isinstance(index[1], toyplot.compatibility.string_type):
                columns = [index[1]]
            # table[, ["a", "b", "c"]], etc.
            else:
                columns = index[1]
        else:
            index = numpy.array(index)
            if issubclass(index.dtype.type, numpy.character):
                columns = index
                row_slice = slice(None, None, None)
            else:
                row_slice = index
                columns = self._columns.keys()

        if row_slice is not None and columns is not None:
            return Table([(column, self._columns[column][row_slice]) for column in columns])


    def __setitem__(self, index, value):
        if isinstance(index, toyplot.compatibility.string_type):
            value = numpy.ma.array(value)
            if value.ndim != 1:
                raise ValueError("Can't assign %s-dimensional array to the '%s' column." % (value.ndim, index))
            for column in self._columns.values():
                if column.shape != value.shape:
                    raise ValueError("Expected %s values, received %s." % (column.shape[0], value.shape[0]))
            column = toyplot.compatibility.unicode_type(index)
            self._columns[column] = value
            return

        if isinstance(index, tuple):
            if isinstance(index[0], toyplot.compatibility.string_type) and isinstance(index[1], (int, slice)):
                column, column_slice = index
                self._columns[column][column_slice] = value
                return

        raise ValueError("Unsupported key for assignment: %s" % (index,))

    def __delitem__(self, key):
        return self._columns.__delitem__(key)

    def __len__(self):
        return list(self._columns.values())[0].shape[0] if len(self._columns) else 0

    def __iter__(self):
        for row in numpy.arange(self.__len__()):
            yield tuple([column[row] for column in self._columns.values()])

    def _repr_html_(self):
        root_xml = xml.Element(
            "table",
            style="border-collapse:collapse; border:none; color: %s" %
            toyplot.color.near_black)
        root_xml.set("class", "toyplot-data-Table")
        header_xml = xml.SubElement(
            root_xml,
            "tr",
            style="border:none;border-bottom:1px solid %s" %
            toyplot.color.near_black)
        for name in self._columns.keys():
            xml.SubElement(
                header_xml,
                "th",
                style="text-align:left;border:none;padding-right:1em;").text = toyplot.compatibility.unicode_type(name)

        iterators = [iter(column) for column in self._columns.values()]
        for row_index in numpy.arange(len(self)):
            for index, iterator in enumerate(iterators):
                value = next(iterator)
                if index == 0:
                    row_xml = xml.SubElement(
                        root_xml, "tr", style="border:none")
                xml.SubElement(
                    row_xml,
                    "td",
                    style="border:none;padding-right:1em;").text = toyplot.compatibility.unicode_type(value)

        return toyplot.compatibility.unicode_type(xml.tostring(root_xml, encoding="utf-8", method="html"), encoding="utf-8")

    @property
    def shape(self):
        """Return the shape (number of rows and columns) of the table.

        Returns
        -------
        shape: (number of rows, number of columns) tuple.
        """
        return (
            list(self._columns.values())[0].shape[0] if len(self._columns) else 0,
            len(self._columns),
        )

    def items(self):
        """Return the table names and columns, in column order.

        Returns
        -------
        items: sequence of (name, column) tuples.
        """
        return self._columns.items()

    def keys(self):
        """Return the table column names, in column order.

        Returns
        -------
        keys: sequence of :class:`str` column names.
        """
        return self._columns.keys()

    def values(self):
        """Return the table columns, in column order.

        Returns
        -------
        values: sequence of :class:`numpy.ndarray` columns.
        """
        return self._columns.values()

    def metadata(self, column):
        """Return metadata for one of the table's columns.

        Parameters
        ----------
        column: string.
          The name of an existing column.

        Returns
        -------
        metadata: :class:`dict` containing key-value pairs.
        """
        if column not in self._columns:
            raise ValueError("Unknown column name '%s'" % column)
        return self._metadata[column]

    def matrix(self):
        """Convert the table to a matrix (2D numpy array).

        The data type of the returned array is chosen based on the types of the
        columns within the table.  Tables containing a homogeneous set of column
        types will return an array of the the same type.  If the table contains one
        or more string columns, the results will be an array of strings.

        Returns
        -------
        matrix: :class:`numpy.ma.core.MaskedArray` with two dimensions.
        """
        return numpy.ma.column_stack(list(self._columns.values()))


def read_csv(fobj, convert=False):
    """Load a CSV (delimited text) file.

    Parameters
    ----------
    fobj: file-like object or string, required
        The file to read.  Use a string filepath, an open file, or a file-like object.
    convert: boolean, optional
        If True, convert column types from string to float where possible.

    Returns
    -------
    table: :class:`toyplot.data.Table`

    Notes
    -----
    read_csv() is a simple tool for use in demos and tutorials.  For more full-featured
    delimited text parsing, you should consider the :mod:`csv` module included in the
    Python standard library, or functionality provided by `numpy` or `Pandas`.
    """
    import csv
    if isinstance(fobj, toyplot.compatibility.string_type):
        fobj = open(fobj, "r")
    rows = [row for row in csv.reader(fobj)]
    columns = zip(*rows)

    result = Table([(column[0], column[1:]) for column in columns])

    if convert:
        for name in result.keys():
            try:
                result[name] = result[name].astype("float64")
            except:
                pass

    return result

