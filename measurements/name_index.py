# -*- coding: utf-8 -*-

import os
import sys
from glob import glob
import pandas as pd
import re
from fuzzywuzzy import fuzz
sys.path.insert(1, os.path.realpath(os.path.join(sys.path[0], os.pardir)))
from measurements.utils import split_path


class NameItem:
    def __init__(self, false_name, true_name, form):
        self.false_name = false_name
        self.true_name = true_name
        self.form = form

    def __str__(self):
        return '\t'.join([self.false_name, self.true_name, self.form])

    def copy(self):
        return NameItem(self.false_name, self.true_name, self.form)


class NameIndex:
    def __init__(self, items=None):
        self.df = pd.DataFrame([], columns=['false_name', 'true_name', 'form'])
        if items is not None:
            for item in items:
                self.add(item)

    def add(self, item):
        """Add an item to index

        Args:
            item: Item instance

        Returns:
            None
        """
        false_name = item.false_name if item.false_name is not None else ''
        true_name = item.true_name if item.true_name is not None else ''
        form = item.form if item.form is not None else ''
        self.df = self.df.append(pd.DataFrame([[false_name, true_name, form]], columns=self.df.columns))

    def update_by_false_name(self, item):
        """Finds items by false name and updates them to the give item."""
        if self.find_by_false_name(item.false_name):
            self.df.loc[self.df['false_name'] == item.false_name] = [item.false_name, item.true_name, item.form]
        else:
            self.add(item)

    @property
    def items(self):
        items = []
        for i, row in self.df.iterrows():
            items.append(NameItem(row['false_name'], row['true_name'], row['form']))
        return items

    @classmethod
    def read_files(cls, glob_pattern):
        index = cls()
        for file in glob(glob_pattern):
            form = None
            path_components = split_path(os.path.abspath(file))
            name = path_components[-1]
            for component in path_components:
                if component in ['onear', 'inear', 'earbud']:
                    form = component
            name = re.sub(r'\.[tc]sv$', '', name)
            item = NameItem(name, name, form)
            index.add(item)
        return index

    @classmethod
    def read_tsv(cls, file_path):
        index = cls()
        df = pd.read_csv(file_path, sep='\t', header=0, encoding='utf-8')
        if not df.columns.all(['false_name', 'true_name', 'form']):
            raise TypeError(f'"{file_path}" columns {df.columns} are corrupted')
        df.fillna('', inplace=True)
        for i, row in df.iterrows():
            index.add(NameItem(row['false_name'], row['true_name'], row['form']))
        return index

    def write_tsv(self, file_path):
        df = self.df.iloc[self.df['false_name'].str.lower().argsort()]
        df.to_csv(file_path, sep='\t', header=True, index=False, encoding='utf-8')

    def find_by_false_name(self, name):
        """Find a single Item by false name

        Args:
            name: False name

        Returns:
            Matching Item or None
        """
        try:
            row = self.df.loc[self.df['false_name'] == name].to_numpy()[0]
            return NameItem(*row)
        except IndexError:
            return None

    def find_by_true_name(self, name):
        """Find all items by their true name.

        Args:
            name: True name

        Returns:
            List of matching NameItems
        """
        arr = self.df.loc[self.df['true_name'] == name].to_numpy()
        return [NameItem(*row) for row in arr]

    def find_by_form(self, form):
        """Find all NameItems by form name

        Args:
            form: Form name

        Returns:
            List of matching NameItems
        """
        arr = self.df.loc[self.df['form'] == form].to_numpy()
        return [NameItem(*row) for row in arr]

    def search_by_false_name(self, name, threshold=80):
        """Finds all items which match closely to given name query

        Args:
            name: Name to find
            threshold: Threshold for matching with FuzzyWuzzy token_set_ratio

        Returns:
            NameIndex with closely matching NameItems
        """
        matches = []
        for item in self.items:
            ratio = fuzz.ratio(item.false_name, name)
            token_set_ratio = fuzz.token_set_ratio(item.false_name.lower(), name.lower())
            if ratio > threshold or token_set_ratio > threshold:
                matches.append([item, ratio, token_set_ratio])
        return sorted(matches, key=lambda x: x[1], reverse=True)
