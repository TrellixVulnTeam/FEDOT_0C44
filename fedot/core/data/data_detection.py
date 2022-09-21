from abc import abstractmethod
from typing import List

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from fedot.core.constants import FRACTION_OF_UNIQUE_VALUES, MIN_VOCABULARY_SIZE
from fedot.core.repository.default_params_repository import DefaultOperationParamsRepository

ALLOWED_NAN_PERCENT = 0.9


class DataDetector:

    @staticmethod
    @abstractmethod
    def prepare_multimodal_data(dataframe: pd.DataFrame, columns: List[str]) -> dict:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def new_key_name(data_part_key: str) -> str:
        raise NotImplementedError()


class TextDataDetector(DataDetector):
    """
    Class for detecting text data during its import.
    """
    def define_text_columns(self, data_frame: pd.DataFrame) -> List[str]:
        """
        :param data_frame: pandas dataframe with data
        :return: list of text columns' names
        """
        text_columns = []
        for column_name in data_frame.columns:
            if self._column_contains_text(data_frame[column_name]):
                text_columns.append(column_name)
        return text_columns

    def define_link_columns(self, data_frame: pd.DataFrame) -> List[str]:
        """
        :param data_frame: pandas dataframe with data
        :return: list of link columns' names
        """
        link_columns = []
        for column_name in data_frame.columns:
            if self.is_link(data_frame[column_name]):
                link_columns.append(column_name)
        return link_columns

    @staticmethod
    def is_full_of_nans(text_data: np.array) -> bool:
        if np.sum(pd.isna(text_data)) / len(text_data) > ALLOWED_NAN_PERCENT:
            return True
        return False

    @staticmethod
    def is_link(text_data: np.array) -> bool:
        if str(next(el for el in text_data if el is not None)).startswith('http'):
            return True
        return False

    @staticmethod
    def prepare_multimodal_data(dataframe: pd.DataFrame, columns: List[str]) -> dict:
        """ Prepares MultiModal text data in a form of dictionary

        :param dataframe: pandas DataFrame to process
        :param columns: list of text columns' names

        :return multimodal_text_data: dictionary with numpy arrays of text data
        """
        multi_modal_text_data = {}

        for column_name in columns:
            text_feature = np.array(dataframe[column_name])
            multi_modal_text_data.update({column_name: text_feature})

        return multi_modal_text_data

    @staticmethod
    def new_key_name(data_part_key: str) -> str:
        return f'data_source_text/{data_part_key}'

    def _column_contains_text(self, column: pd.Series) -> bool:
        """
        Column contains text if:
        1. it's not float or float compatible
        (e.g. ['1.2', '2.3', '3.4', ...] is float too)
        2. fraction of unique values (except nans) is more than 0.6
        3. size of tfidf vocabulary is more than 20

        If size of tfidf vocabulary is less than 20, then it is probably
        text column too, but it cannot be vectorized and used in model

        :param column: pandas series with data
        :return: True if column contains text, False otherwise or if column contains links
        """
        if self.is_link(column):
            return False
        elif column.dtype == object and not self._is_float_compatible(column) and self._has_unique_values(column):
            try:
                params = DefaultOperationParamsRepository().get_default_params_for_operation('tfidf')
                tfidf_vectorizer = TfidfVectorizer(**params)
                tfidf_vectorizer.fit(np.where(pd.isna(column), '', column))
                if len(tfidf_vectorizer.vocabulary_) > MIN_VOCABULARY_SIZE:
                    return True
            except ValueError:
                print(f'Column {column.name} possibly contains text, but it is not possible to vectorize it')
        return False

    @staticmethod
    def _is_float_compatible(column: pd.Series) -> bool:
        """
        :param column: pandas series with data
        :return: True if column contains only float or nan values
        """
        nans_number = column.isna().sum()
        converted_column = pd.to_numeric(column, errors='coerce')
        result_nans_number = converted_column.isna().sum()
        failed_objects_number = result_nans_number - nans_number
        non_nan_all_objects_number = len(column) - nans_number
        failed_ratio = failed_objects_number / non_nan_all_objects_number
        return failed_ratio < 0.5

    @staticmethod
    def _has_unique_values(column: pd.Series) -> bool:
        """
        :param column: pandas series with data
        :return: True if number of unique column values > threshold
        """
        unique_num = len(column.unique())
        nan_num = pd.isna(column).sum()
        return unique_num / len(column) > FRACTION_OF_UNIQUE_VALUES if nan_num == 0 \
            else (unique_num - 1) / (len(column) - nan_num) > FRACTION_OF_UNIQUE_VALUES


class TimeSeriesDataDetector(DataDetector):
    """
    Class for detecting time series data during its import.
    """

    @staticmethod
    def prepare_multimodal_data(dataframe: pd.DataFrame, columns: List[str]) -> dict:
        """ Prepares MultiModal data for time series forecasting task in a form of dictionary

        :param dataframe: pandas DataFrame to process
        :param columns: column names, which should be used as features in forecasting

        :return multi_modal_ts_data: dictionary with numpy arrays
        """
        multi_modal_ts_data = {}
        for column_name in columns:
            feature_ts = np.array(dataframe[column_name])
            idx = list(dataframe['datetime'])

            # Will be the same
            multi_modal_ts_data.update({column_name: feature_ts})

        multi_modal_ts_data['idx'] = np.asarray(idx)

        return multi_modal_ts_data

    @staticmethod
    def new_key_name(data_part_key: str) -> str:
        if data_part_key == 'idx':
            return 'idx'
        return f'data_source_ts/{data_part_key}'
