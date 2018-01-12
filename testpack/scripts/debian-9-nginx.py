#!/usr/bin/env python3

import unittest
import os
import docker
from selenium import webdriver
import os.path
import tarfile
from io import BytesIO


class Test1and1ApacheImage(unittest.TestCase):
    container = None
    container_ip = None

    @classmethod
    def setUpClass(cls):
        image_to_test = os.getenv("IMAGE_NAME")
        if image_to_test == "":
            raise Exception("I don't know what image to test")

        client = docker.from_env()
        Test1and1ApacheImage.container = client.containers.run(
            image=image_to_test,
            remove=True,
            detach=True,
            network_mode="bridge"
        )
        Test1and1ApacheImage.copy_test_files("testpack/files/html", "test.html", "/var/www/html")

        details = docker.APIClient().inspect_container(container=Test1and1ApacheImage.container.id)
        Test1and1ApacheImage.container_ip = details['NetworkSettings']['IPAddress']

    @classmethod
    def copy_test_files(cls, startfolder, relative_source, dest):
        # Change to the start folder
        pwd = os.getcwd()
        os.chdir(startfolder)
        # Tar up the request folder
        pw_tarstream = BytesIO()
        with tarfile.open(fileobj=pw_tarstream, mode='w:gz') as tf:
            tf.add(relative_source)
        # Copy the archive to the correct destination
        docker.APIClient().put_archive(
            container=Test1and1ApacheImage.container.id,
            path=dest,
            data=pw_tarstream.getvalue()
        )
        # Change back to original folder
        os.chdir(pwd)

    @classmethod
    def tearDownClass(cls):
        Test1and1ApacheImage.container.stop()

    def setUp(self):
        print ("\nIn method", self._testMethodName)
        self.container = Test1and1ApacheImage.container

    def execRun(self, command):
        return self.container.exec_run(command).decode('utf-8')

    def assertPackageIsInstalled(self, packageName):
        op = self.execRun("dpkg -l %s" % packageName)
        self.assertTrue(
            op.find(packageName) > -1,
            msg="%s package not installed" % packageName
        )

    def file_mode_test(self, filename: str, mode: str):
        # Compare (eg) drwx???rw- to drwxr-xrw-
        result = self.execRun("ls -ld %s" % filename)
        self.assertFalse(
            result.find("No such file or directory") > -1,
            msg="%s is missing" % filename
        )
        for char_count in range(0, len(mode)):
            self.assertTrue(
                mode[char_count] == '?' or (mode[char_count] == result[char_count]),
                msg="%s incorrect mode: %s" % (filename, result)
            )

    def file_content_test(self, filename: str, content: list):
        result = self.execRun("cat %s" % filename)
        self.assertFalse(
            result.find("No such file or directory") > -1,
            msg="%s is missing" % filename
        )
        for search_item in content:
            self.assertTrue(
                result.find(search_item) > -1,
                msg="Missing : %s" % search_item
            )

    # <tests to run>

    def test_docker_logs(self):
        expected_log_lines = [
            "run-parts: executing /hooks/entrypoint-pre.d/00_check_euid",
            "run-parts: executing /hooks/entrypoint-pre.d/01_ssmtp_setup",
            "run-parts: executing /hooks/entrypoint-pre.d/02_user_group_setup",
            "run-parts: executing /hooks/entrypoint-pre.d/19_doc_root_setup",
            "run-parts: executing /hooks/entrypoint-pre.d/20_ssl_setup",
            "run-parts: executing /hooks/supervisord-pre.d/21_cleanup_log_files",
            "Loading nginx config",
        ]
        container_logs = self.container.logs().decode('utf-8')
        for expected_log_line in expected_log_lines:
            self.assertTrue(
                container_logs.find(expected_log_line) > -1,
                msg="Docker log line missing: %s from (%s)" % (expected_log_line, container_logs)
            )

    def test_nginx_conf(self):
        self.file_content_test(
            "/etc/nginx/nginx.conf",
            [
                "daemon off;"
            ]
        )

    def test_nginx_site_conf(self):
        self.file_content_test(
            "/etc/nginx/sites-enabled/site.conf",
            [
                "listen 8080",
                "listen [::]:8080"
            ]
        )

    def test_nginx_var_log_nginx(self):
        self.file_mode_test("/var/log/nginx", "drwxrwxrwx")

    def test_nginx_var_lib_nginx(self):
        self.file_mode_test("/var/lib/nginx", "drwxrwxrwx")

    def test_nginx_var_www_html(self):
        self.file_mode_test("/var/www/html", "drwxrwxrwx")

    def test_nginx_installed(self):
        self.assertPackageIsInstalled("nginx")

    def test_nginx_pid_file(self):
        self.file_mode_test("/var/run/nginx.pid", "-") # This is enough to check that it exists and is a file

    def test_nginx_get(self):
        driver = webdriver.PhantomJS()
        driver.get("http://%s:8080/test.html" % Test1and1ApacheImage.container_ip)
        self.assertEqual('Success', driver.title)

    def test_nginx_cgi_headers(self):
        # We need to set the desired headers, then get a new driver for this to work
        webdriver.DesiredCapabilities.PHANTOMJS['phantomjs.page.customHeaders.X-Forwarded-For'] = "1.2.3.4"
        webdriver.DesiredCapabilities.PHANTOMJS['phantomjs.page.customHeaders.X-Forwarded-Port'] = "99"
        driver = webdriver.PhantomJS()
        driver.get("http://%s:8080/test.html" % Test1and1ApacheImage.container_ip)
        self.assertEqual(
            self.execRun('bash -c "grep 1.2.3.4 /var/log/nginx/*.log | grep -iq phantomjs && echo -n true"'),
            "true",
            msg="Missing 1.2.3.4 from logs"
        )

        # </tests to run>

if __name__ == '__main__':
    unittest.main(verbosity=1)
