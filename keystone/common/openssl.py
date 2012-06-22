import os
import stat
import subprocess
import sys
import stat

from keystone import config

CONF = config.CONF


def file_exists(file_path):
    sys.stdout.write("Looking for %s:\t" % file_path)
    if os.path.exists(file_path):
        print("[FOUND]")
        return True
    else:
        print("[NOT FOUND]")
        return False


DEFAUILT_SUBJECT = "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com"


class ConfigureSSL(object):

    def __init__(self, *args, **kw):
        self.conf_dir = os.path.dirname(CONF.signing.ca_certs)
        self.ssl_config_file_name = self.conf_dir + "/openssl.conf"
        self.ca_key_file = self.conf_dir + "/cakey.pem"
        self.request_file_name = self.conf_dir + "/req.pem"
        self.ssl_dictionary = \
            {
             'conf_dir': self.conf_dir,
             "ca_cert": CONF.signing.ca_certs,
             "ssl_config": self.ssl_config_file_name,
             "ca_private_key": self.ca_key_file,
             "ca_cert_cn": "hostname",
             "request_file": self.request_file_name,
             "signing_key": CONF.signing.keyfile,
             "signing_cert": CONF.signing.certfile,
             "default_subject": DEFAUILT_SUBJECT
             }

    def exec_command(self, command):
        to_exec = command % self.ssl_dictionary
        print (to_exec)
        subprocess.check_call(to_exec.rsplit(" "))

    def build_ssl_config_file(self):
        if not file_exists(self.ssl_config_file_name):
            ssl_config_file = open(self.ssl_config_file_name, 'w')
            ssl_config_file.write(self.sslconfig % self.ssl_dictionary)
            ssl_config_file.close()

        index_file_name = self.conf_dir + "/index.txt"
        if not file_exists(index_file_name):
            index_file = open(index_file_name, 'w')
            index_file.write("")
            index_file.close()

        serial_file_name = self.conf_dir + "/serial"
        if not file_exists(serial_file_name):
            index_file = open(serial_file_name, 'w')
            index_file.write("01")
            index_file.close()

    def build_ca_cert(self):
        if not file_exists(CONF.signing.ca_certs):
            if not os.path.exists(self.ca_key_file):
                self.exec_command("openssl genrsa -out %(ca_private_key)s "\
                                  "2048 -config %(ssl_config)s")
                os.chmod("%(ca_private_key)s" % \
                         self.ssl_dictionary, stat.S_IRUSR)
            print("Generating CA certificate")
            self.exec_command('openssl req -new -x509 -extensions v3_ca ' \
                              '-passin pass:1234 ' \
                              '-key %(ca_private_key)s -out %(ca_cert)s '\
                              '-days 3650 ' \
                              '-config %(ssl_config)s ' \
                              '-subj %(default_subject)s')

    def build_private_key(self):
        if not file_exists(CONF.signing.keyfile):
            self.exec_command("openssl genrsa -out %(signing_key)s 2048"\
                              " -config %(ssl_config)s")

    def build_signing_cert(self):
        if not file_exists(CONF.signing.certfile):
            self.exec_command("openssl req -key %(signing_key)s -new -nodes "\
                              "-out %(request_file)s -config %(ssl_config)s "\
                         "-subj %(default_subject)s")
            self.exec_command("openssl ca -batch -out %(signing_cert)s "\
                              "-config %(ssl_config)s "\
                              "-infiles %(request_file)s")

    def run(self):
        self.build_ssl_config_file()
        self.build_ca_cert()
        self.build_private_key()
        self.build_signing_cert()

    def erase(self):
        for file in [self.ssl_config_file_name,
                     self.request_file_name,
                     self.ca_key_file,
                     CONF.signing.ca_certs,
                     CONF.signing.keyfile,
                     CONF.signing.certfile,
                     self.conf_dir + ""]:
            if os.path.exists(file):
                os.remove(file)

    sslconfig = "" \
        "# OpenSSL configuration file.\n" \
        "#\n" \
        "\n" \
        "# Establish working directory.\n" \
        "\n" \
        "dir            = %(conf_dir)s \n" \
        "[ ca ]\n"\
        "default_ca        = CA_default\n"\
        "\n"\
        "[ CA_default ]\n"\
        "new_certs_dir     = $dir \n"\
        "serial            = $dir/serial\n"\
        "database          = $dir/index.txt\n"\
        "certificate       = %(ca_cert)s\n"\
        "private_key       = %(ca_private_key)s \n"\
        "default_days      = 365\n"\
        "default_md        = md5\n"\
        "preserve          = no\n"\
        "email_in_dn       = no\n"\
        "nameopt           = default_ca\n"\
        "certopt           = default_ca\n"\
        "policy            = policy_match\n"\
        "[ policy_match ]\n"\
        "countryName             = match\n"\
        "stateOrProvinceName     = match\n"\
        "organizationName        = match\n"\
        "organizationalUnitName  = optional\n"\
        "commonName              = supplied\n"\
        "emailAddress            = optional\n"\
        "\n"\
        "[ req ]\n"\
        "default_bits        = 1024 # Size of keys \n"\
        "default_keyfile        = key.pem # name of generated keys\n"\
        "default_md        = md5 # message digest algorithm\n"\
        "string_mask        = nombstr # permitted characters\n"\
        "distinguished_name    = req_distinguished_name\n"\
        "req_extensions        = v3_req\n"\
        "\n"\
        "[ req_distinguished_name ]\n"\
        "0.organizationName    = Organization Name (company)\n"\
        "organizationalUnitName    = Organizational Unit Name "\
            "(department, division)\n"\
        "emailAddress        = Email Address\n"\
        "emailAddress_max    = 40\n"\
        "localityName        = Locality Name (city, district)\n"\
        "stateOrProvinceName    = State or Province Name (full name)\n"\
        "countryName        = Country Name (2 letter code)\n"\
        "countryName_min        = 2\n"\
        "countryName_max        = 2\n"\
        "commonName        = Common Name (hostname, IP, or your name)\n"\
        "commonName_max        = 64\n"\
        "# Default values for the above, for consistency and less typing. \n"\
        "0.organizationName_default = Openstack, Inc\n"\
        "localityName_default = Undefined\n"\
        "stateOrProvinceName_default = Undefined\n"\
        "countryName_default = US\n"\
        "commonName_default = %(ca_cert_cn)s\n"\
        "\n"\
        "[ v3_ca ] \n"\
        "basicConstraints = CA:TRUE \n"\
        "subjectKeyIdentifier = hash \n"\
        "authorityKeyIdentifier = keyid:always,issuer:always\n"\
        "\n"\
        "[ v3_req ] \n"\
        "basicConstraints = CA:FALSE \n"\
        "subjectKeyIdentifier = hash\n"
