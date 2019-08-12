"""
DANGER: Note that everything here assumes exclusive access to your dynalist. If
you are editing your dynalist from multiple places at once (including with
multiple copies of this library), you might damage your data!
"""

"""dynalist.py"""

import json
import textwrap

import requests


class DynalistError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class File(object):
    def __init__(self, session, file_id, permission):
        self.session = session
        self.file_id = file_id
        self.permission = permission

    @property
    def is_folder(self):
        raise NotImplementedError("concrete File classes must implement is_folder()")


class Folder(File):
    def __init__(
            self,
            session,
            file_id,
            children,
            title=None,
            permission=4,
            collapsed=False,
            ):
        super().__init__(session, file_id, permission)
        self.children = children
        self.title = title
        self.permission = permission
        self.collapsed = collapsed

    def is_folder(self):
        return True

    def is_root(self):
        return self.title is None

    def __str__(self):
        res = []
        res.append(self.title + ":")
        for c in self.children:
            res.append(textwrap.indent(str(c), "  "))
        return "\n".join(res)


class Document(File):
    def __init__(self, session, file_id, title, permission):
        super().__init__(session, file_id, permission)
        self.title = title
        self._contents = None

    @property
    def contents(self):
        if self._contents is None:
            res = self.session.read_document(self.file_id)
            self.title = res["title"]
            nodes = {}
            for node in res["nodes"]:
                nodes[node["id"]] = ExistingNode(node)
            self._contents = nodes
        return self._contents

    def is_folder(self):
        return False

    def __str__(self):
        return self.title


class ExistingNode(object):
    def __init__(self, info):
        self.content = info["content"]
        self.created = info["created"]
        self.modified = info["modified"]
        self.children = info.get("children") or []

        self.note = info.get("note")
        if info.get("checkbox"):
            self.checked = info.get("checked")
        self.color = info.get("color")
        self.heading = info.get("heading")


class SubTree(object):
    def __init__(self, doc, root_id):
        self.node = doc.contents[root_id]
        self.children = [SubTree(doc, child_id) for child_id in self.node.children]


class InsertNode(object):
    def __init__(
            self,
            parent_id,
            content,
            note=None,
            checked=None,
            heading=None,
            color=None
            ):
        self.parent_id = parent_id
        self.content = content
        self.note = note
        self.checked = checked
        self.heading = heading
        self.color = color

    def from_existing_node(node, new_parent=None):
        pass

    def as_dict(self):
        result = {"action": "insert"}
        for k in ["parent_id", "content", "note", "heading", "color"]:
            if getattr(self, k) is not None:
                result[k] = getattr(self, k)
        if self.checked is not None:
            result["checkbox"] = True
            result["checked"] = self.checked
        return result


def check_ok(res):
    code = res["_code"]
    if not code.lower() == "ok":
        raise DynalistError(code, res["_msg"])


class Session(object):
    def __init__(self, token, api_url="https://dynalist.io/api/v1"):
        self.token = token
        self.FILE_LIST = api_url + "/file/list"
        self.FILE_EDIT = api_url + "/file/edit"
        self.DOC_READ = api_url + "/doc/read"
        self.DOC_EDIT = api_url + "/doc/edit"
        self.INBOX_ADD = api_url + "/inbox/add"

    def request(self, url, **data):
        msg = {}
        msg.update({"token": self.token})
        msg.update(data)
        headers = {"Content-Type": "application/json"}
        return requests.post(url, headers=headers, data=json.dumps(msg)).json()

    def list_files(self):
        return self.request(self.FILE_LIST)

    def read_document(self, file_id):
        return self.request(self.DOC_READ, file_id=file_id)

    def change_document(self, file_id, changes):
        return self.request(
                self.DOC_EDIT,
                file_id=file_id,
                changes=[c.as_dict() for c in changes],
                )

    def send_to_inbox(self, index, node):
        return self.request(self.INBOX_ADD, index=index, **node.as_dict())


class Dynalist(object):
    def __init__(self, token):
        self.session = Session(token)

    def get_files(self):
        resp = self.session.list_files()
        root = resp["root_file_id"]
        fs = resp["files"]
        fs_by_id = {}
        for f in fs:
            fs_by_id[f["id"]] = f

        files_by_id = {}
        def build_file(file_id):
            f = fs_by_id[file_id]
            if f["type"] == "document":
                res = Document(
                        self.session, file_id, f["title"], f["permission"])
                files_by_id[file_id] = res
                return res
            children = [build_file(child_id) for child_id in f["children"]]
            res = Folder(
                    self.session,
                    file_id,
                    children,
                    title=f["title"],
                    permission=f["permission"],
                    collapsed=f["collapsed"],
                    )
            files_by_id[file_id] = res
            return res

        return (build_file(root), files_by_id)
