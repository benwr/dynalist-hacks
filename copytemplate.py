import copy
import datetime
import os
import pathlib

import dotenv

import dynalist as dl

"""copytemplate.py"""


def find_node_by_title(doc, content):
    result = None
    for k, node in doc.contents.items():
        if node.content == content:
            result = node
            break
    return result


def insert_subtree(session, doc, subtree, parent_id):
    insertion = dl.InsertNode.from_existing_node(subtree.node, new_parent=parent_id)
    res = session.change_document(doc.file_id, [insertion])
    new_id = res["new_node_ids"][0]
    # insertions happen at the front for some reason
    for child in reversed(subtree.children):
        insert_subtree(session, doc, child, new_id)


def do_replacement(session, doc):
    template_node = find_node_by_title(doc, "[daily review]")
    if template_node is None:
        raise KeyError("[daily review] not found as a node")

    # this is overkill but whatever:
    template_subtree = copy.deepcopy(dl.SubTree(doc, template_node.node_id))

    pdt = datetime.timezone(-datetime.timedelta(hours=8))
    now = datetime.datetime.now(tz=pdt)
    oneday = datetime.timedelta(days=1)
    tomorrow = now + oneday

    template_subtree.node.content = tomorrow.strftime("%Y-%m-%d")

    parent_node = find_node_by_title(doc, "Daily Reviews")
    if parent_node is None:
        raise KeyError("Daily Reviews not found as a node")

    insert_subtree(session, doc, template_subtree, parent_node.node_id)


def main():
    env_path = pathlib.Path('.')/'secrets.env'
    dotenv.load_dotenv(dotenv_path=env_path)

    d = dl.Dynalist(os.getenv("DYNALIST_KEY"))
    files = d.get_files()[1]
    for k, f in files.items():
        if f.title == "Fake Reviews and Goals":
            do_replacement(d.session, f)
            break


if __name__ == "__main__":
    main()
