"""Best-effort persistent history of native drawings successfully opened/saved."""
import json
import os
from pathlib import Path
import sys
import tempfile


def preferences_path():
    if sys.platform=='darwin':root=Path.home()/'Library'/'Application Support'
    elif sys.platform=='win32':root=Path(os.environ.get('APPDATA',str(Path.home()/'AppData'/'Roaming')))
    else:root=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
    return root/'BrianCAD'/'recent-files.json'


class RecentFiles:
    def __init__(self,path=None,limit=10):
        self.path=Path(path) if path is not None else preferences_path();self.limit=limit;self.paths=[]
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(data,dict) and data.get('version')==1 and isinstance(data.get('paths'),list):
                for value in data['paths']:
                    if isinstance(value,str) and value and '\0' not in value:
                        name=os.path.abspath(os.path.expanduser(value))
                        if os.path.normcase(name) not in {os.path.normcase(p) for p in self.paths}:self.paths.append(name)
                        if len(self.paths)>=limit:break
        except (OSError,ValueError,TypeError):pass

    def remember(self,path):
        name=os.path.abspath(os.path.expanduser(os.fspath(path)))
        self.paths=[name]+[p for p in self.paths if os.path.normcase(p)!=os.path.normcase(name)]
        del self.paths[self.limit:];self.write()

    def clear(self):self.paths=[];self.write()

    def write(self):
        temporary=None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=self.path.parent,delete=False) as f:
                temporary=f.name;json.dump({'version':1,'paths':self.paths},f,ensure_ascii=True,indent=2)
            os.replace(temporary,self.path)
        except OSError:pass  # A preferences failure must not turn a successful save into an error.
        finally:
            if temporary and os.path.exists(temporary):
                try:os.unlink(temporary)
                except OSError:pass
