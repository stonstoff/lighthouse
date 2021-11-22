import os
import time
import urequests as requests
import ujson as json

"""
"ota": {
    "base_url": "https://micropython-continuous-delivery.s3-ap-southeast-1.amazonaws.com/",
    "check_frequency": 30
}
"""

class HttpOTA:
    def __init__(self, device_name, ota_config, **kwargs):
        if len(device_name) == 0:
            raise Exception("Device name not configured")

        self.device_name = device_name

        if not 'base_url' in ota_config:
            raise Exception("OTA Base URL not configured")
        else:
            self.base_url = ota_config['base_url']

        if not 'check_frequency' in ota_config:
            print("No check frequency specified - assuming 300s")
            self.check_frequency = 300
        else:
            self.check_frequency = ota_config['check_frequency']

    def update(self, force = False):
        self.load_local_manifest()
        print(self.manifest)

        now = time.mktime(time.gmtime())

        print(now)
        print(self.manifest['last_update_check'])
        print(self.check_frequency)

        if force:
            print('forced')
            self.check_and_update()
        elif now > (self.manifest['last_update_check'] + self.check_frequency):
            print('scheduled')
            self.check_and_update()
        else:
            print('skip: %s vs %s' % (now - self.manifest['last_update_check'], self.check_frequency))

    def check_and_update(self):
        print(self.remote_manifest_url())

        self.get_remote_manifest()
        if not self.remote_manifest:
            print("Problems getting remote manifest")
            return

        if self.versions_differ():
            self.download_and_write_update()
        else:
            print("no update required")

        self.commit_manifest()

        print(self.remote_manifest)

    def next_package_url(self):
        return self.remote_manifest['package_url']

    def download_and_write_update(self):
        print("Updating from: %s" % self.next_package_url())

        self.download_and_save_package(self.next_package_url())
        self.extract_files()

        print("deleting package.tar")
        os.remove("package.tar")

    def download_and_save_package(self, path):
        print("Source: %s" % path)
        fp = open('package.tar', 'wb')
        bytes = fp.write(requests.get(path).content)
        fp.close()
        print("Wrote %s bytes" % bytes)

    def extract_files(self):
        import utarfile
        tf = utarfile.TarFile('package.tar')

        for i in tf:
            if i.type == utarfile.DIRTYPE:
                print("mkdir: %s" % i.name)
                try:
                    os.mkdir(i.name)
                except:
                    pass
            else:

                try:
                    print("deleting: %s" % i.name)
                    os.remove(i.name)
                except:
                    pass

                f = tf.extractfile(i)
                contents = f.read()

                print("writing: %s" % i.name)
                fp = open(i.name, 'wb')
                bytes = fp.write(contents)
                fp.close()
                print("Wrote %s bytes to %s" % (bytes, i.name))


    def commit_manifest(self):
        self.manifest = self.remote_manifest
        self.manifest['last_update_check'] = time.mktime(time.gmtime())

        print("going to update the manifest")
        print(self.manifest)
        with open("manifest.json", 'w') as new_manifest_fp:
            json.dump(self.remote_manifest, new_manifest_fp)
            print("wrote new manifest")

    def versions_differ(self):
        if self.manifest['version'] != self.remote_manifest['version']:
            print("Version difference: %s vs %s" % (self.manifest['version'], self.remote_manifest['version']))
            return True

    def remote_manifest_url(self):
        return "".join([self.base_url, self.device_name, ".json"])

    def get_remote_manifest(self):
        try:
            self.remote_manifest = requests.get(self.remote_manifest_url()).json()
        except ValueError as error:
            print("Got invalid JSON")
            self.remote_manifest = False
            return

    def load_local_manifest(self):
        self.manifest = {}
        if 'manifest.json' in os.listdir():
            with open('manifest.json', 'r') as current_manifest_fp:
                try:
                    self.manifest = json.load(current_manifest_fp)
                except:
                    print("Error in reading local manifest.json")
                    pass

        if 'version' not in self.manifest:
            self.manifest['version'] = None

        if 'last_update_check' not in self.manifest:
            self.manifest['last_update_check'] = 0
