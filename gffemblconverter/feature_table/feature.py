#!/usr/bin/env python3
"""Feature object for EMBL feature tables
"""

import copy
import logging
from Bio.SeqIO import InsdcIO

from .embl_utilities import embl_line

class Feature():
    """Feature object for EMBL feature tables.

    From http://www.insdc.org/files/feature_table.html#3.2:
    "Feature keys indicate
    (1) the biological nature of the annotated feature or
    (2) information about changes to or other versions of the sequence.
    The feature key permits a user to quickly find or retrieve similar features or
    features with related functions. "
    """

    QUALIFIER_TEMPLATES = {}

    def __init__(self, definition):
        """
        Initializes a Feature from a defintion.
        """
        self.identifier = None
        self.location = None
        self.name = definition['feature_key']
        self.qualifiers = []
        self.translations = []
        self.optional_qualifiers = {}
        self.mandatory_qualifiers = {}
        for key, value in definition.items():
            setattr(self, key, value)

    def __repr__(self):
        information = f"{self.name:<16}{self.embl_location(self.location)}"

        output = embl_line("FT", information, add_spacer=False)
        for qualifier in self.qualifiers:
            output += f"{qualifier}"
        return output

    def add_translations(self, translations):
        """
        Adds translation dictionaries which will direct how input data fields
        are mapped to EMBL fields.
        """
        self.translations = translations

    @staticmethod
    def embl_location(location, rec_length=None):
        """
        Formats a FeatureLocation as an EMBL location by calling the
        InsdcIO._insdc_location_string function in biopython. I'd prefer to not
        call a private function here, but I haven't figured out how to properly
        do this in any other way.
        """
        if rec_length is None:
            rec_length = location.end
        return InsdcIO._insdc_location_string(location, rec_length)

    def update_values(self, seq_feature):
        """
        Attempts to update all legal values in the Feature from the
        information in a Bio.SeqFeature.
        """
        if not hasattr(self, "optional_qualifiers"):
            raise ValueError(("Qualifiers are required to have the "
                              "optional_qualifiers dictionary."))

        # update own identifier to the seq_feature's id
        self.identifier = seq_feature.id

        # update own location to the seq_feature's location
        self.set_location(seq_feature.location)

        # add all legal qualifiers
        for qualifier, value in seq_feature.qualifiers.items():
            self.set_qualifier(qualifier, value)

    def set_location(self, seq_location):
        """
        Updates the features location with a seq_location.
        """
        self.location = seq_location

    def set_qualifier(self, qualifier, value, prefix=""):
        """
        Adds a legal qualifier value to the feature, given that it has a
        template in the self.optional_qualifiers or self.mandatory_qualifiers
        dictionaries.

        If the qualifier is unknown, the translations['qualifiers'] dictionary
        will be used to try to find a mapping to a legal qualifier.
        """
        if qualifier not in self.optional_qualifiers or \
           qualifier not in self.mandatory_qualifiers:
            translations = self.translations.get('qualifiers', [])
            if qualifier not in translations:
                logging.warning(("Qualifier %s is neither an optional nor a "
                                 "mandatory qualifier of %s"),
                                qualifier, self.name)
                return
            if translations[qualifier].get("target", ""):
                prefix = translations[qualifier].get("prefix", prefix)
                logging.debug("Translated qualifier %s to %s", qualifier,
                              translations[qualifier]["target"])
                qualifier = translations[qualifier]["target"]
            else:
                logging.info("Qualifier %s has no translation target",
                             qualifier)
                return

        if qualifier not in Feature.QUALIFIER_TEMPLATES:
            logging.error("Legal qualifier %s not found in qualifier cache!",
                          qualifier)
            raise ValueError(f"Legal qualifier {qualifier} not found in cache.")

        if not isinstance(value, list):
            value = [value]

        # add prefixes to values
        for i, val in enumerate(value):
            value[i] = f"{prefix}{val}"

        template = copy.deepcopy(Feature.QUALIFIER_TEMPLATES[qualifier])
        template.set_value(value)

        self.qualifiers += [template]