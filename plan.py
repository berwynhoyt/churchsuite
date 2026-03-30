#!/usr/bin/env python3
""" Fetch the next service plan from ChurchSuite and output it as a word document """

import pprint
import argparse
import logging
import textwrap

from datetime import date, timedelta

import churchsuite as cs
import secrets
import pathvalidate
import docx

def plan2docx(plan, quiet=False):
    """ Save service plan to MS Word .docx file for easier markup by the service leader.
        The output is also less noisy than the pdf plan exported by ChurchSuite.
    """
    title = f"{plan.date} {plan.name}{' (draft)' if plan.status=='draft' else ''}"
    filename = pathvalidate.sanitize_filename(title) + '.docx'
    if not quiet:
        print(f"Creating {filename}")
    doc = docx.Document()

    doc.add_heading(title)
    items = db.get(cs.URL.plan_items, params={'plan_ids[]':plan.id})
    for item in items:
        names = [f"{person.first_name} {person.last_name}" for person in item.people or []]
        doc.add_heading(f"{item.name} ({','.join(names)})", level=1)
        logging.info(pprint.pformat(item))
        for q in getattr(item, 'question_responses') or ():
            for section, words in cs.item_sections(item).items():
                doc.add_heading(section, level=2)

    doc.save(filename)
    return filename

def plan2txt(plan):
    """ Print service plan as txt. This is mainly for developer tinkering. """
    print(f"{plan.date} {plan.name} {' (draft)' if status=='draft' else ''}:")
    items = db.get(cs.URL.plan_items, params={'plan_ids[]':plan.id})
    for item in items:
        names = [f"{person.first_name} {person.last_name}" for person in item.people or []]
        print(f"{item.name} ({','.join(names)})")
        logging.info(pprint.pformat(item))
        for q in getattr(item, 'question_responses') or ():
            for section, words in cs.item_sections(item).items():
                print(textwrap.indent(f"*{section}*: {words}", '  '))

def upcoming_services(db):
    """ Get all published and draft plans for the next week and output them as Word .docx files for easier markup.
        These are less noisy than the default Churchsuite 
    """
    today = date.today()
    plans = []
    for status in ('published', 'draft'):
        plans += db.get(cs.URL.plans, status=status, starts_after=str(today), starts_before=str(today + timedelta(days=7)), per_page=1)
    if not plans:
        sys.exit("There is no plan in ChurchSuite for the coming week")
    return plans

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity level (e.g., -vv)")
    args = parser.parse_args()
    # Set logging level based on -v flag
    log_level = logging.WARNING - 10*args.verbose
    logging.basicConfig(level=log_level, format=f'%(levelname)s: %(message)s')

    db = cs.Churchsuite(auth=(secrets.CLIENT_ID, secrets.CLIENT_SECRET))
    for plan in upcoming_services(db):
        plan2docx(plan)
