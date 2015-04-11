#!/usr/bin/python2

import Milter
import StringIO
import email
import shutil
import gnupg
import tempfile
import os
import argparse
from setproctitle import setproctitle
from syslog import syslog, openlog, LOG_MAIL

openlog('encryption-milter', facility=LOG_MAIL)
setproctitle("encryption-milter")

class EncryptionMilter(Milter.Base):

  def __init__(self, mailkeyring_filename):
    self.bodyBuffer = None
    self.mailkeyring_filename = mailkeyring_filename
    self.receipientWantsEncryption=False

  def envfrom(self, sender, *esmtpParams):
    self.bodyBuffer = StringIO.StringIO()
    return Milter.CONTINUE

  @Milter.noreply
  def header(self, field, value):
    self.bodyBuffer.write('%s: %s\n' % (field, value))
    if field.lower() == 'to':
      if 'foo@bar.com' in value.lower():
        self.receipientWantsEncryption=True
    return Milter.CONTINUE

  @Milter.noreply
  def eoh(self):
    self.bodyBuffer.write('\n')
    return Milter.CONTINUE

  @Milter.noreply
  def body(self, chunk):
    self.bodyBuffer.write(chunk)
    return Milter.CONTINUE

  def eom(self):
    self.bodyBuffer.seek(0)
    message = email.message_from_file(self.bodyBuffer)

    if message.is_multipart():
      syslog('Multipart message, skipped.')

      return Milter.CONTINUE
    else:
      if self.receipientWantsEncryption == True:
        messageContent = message.get_payload()
        
        if not ('-----BEGIN PGP MESSAGE-----' in messageContent):
          syslog('Encrypting message.');
          encryptedContent = self.encrypt(messageContent)
          self.replacebody(encryptedContent)
          return Milter.ACCEPT
        else:
          syslog('Already encrypted message, skipped.');
          return Milter.CONTINUE
      else:
        syslog('Mail receipient is not configured to receive encrypted mail, skipped.')
        return Milter.CONTINUE

  def encrypt(self, message):
    try:
      gpgdir = tempfile.mkdtemp()

      gpg = gnupg.GPG(gnupghome=gpgdir)
      gpg.decode_errors="ignore"
      
      with open(self.mailkeyring_filename,'r') as mailkeyring_file:        
        mailkeyring_key_data = mailkeyring_file.read()
        mailkeyring = gpg.import_keys(mailkeyring_key_data)
        result = gpg.encrypt(message, mailkeyring.fingerprints, always_trust=True).data
    
    finally:
      shutil.rmtree(gpgdir)
    
    return result

class PidFile:

  def __init__(self, filepath):
    self.filepath = filepath

  def __enter__(self):
    if os.path.isfile(self.filepath):
      raise Exception('pid file exists already. possibly another process is already running.')

    with open(self.filepath, "w") as pidfile:
      pidfile.write(str(os.getpid()))
    
    return self

  def __exit__(self, type, value, traceback):
    if os.path.isfile(self.filepath) and not os.path.islink(self.filepath):
       os.unlink(self.filepath)

def parseArgs():
  parser = argparse.ArgumentParser(description='encryption-milter', epilog='For bugs. see christoph@nerdtools.de')
  
  parser.add_argument(
    '--pidfile', 
    '-P', 
    action='store', 
    default='/var/run/encryption-milter.pid', 
    help='pidfile to create'
  )

  parser.add_argument(
    '--keyring', 
    '-K', 
    action='store', 
    default='/etc/encryption-milter-keyring.pub', 
    help='keyring gpg file containing the public key for encryption'
  )

  parser.add_argument(
    '--socket', 
    '-S', 
    action='store', 
    default='inet:9000@127.0.0.1',
    help='socket to bind to'
  )
  
  return parser.parse_args()

def main():
  syslog('Starting daemon')

  try:
    args = parseArgs()
      
    with PidFile(args.pidfile) as pidfile:
      def createMilter():
        return EncryptionMilter(args.keyring)
      
      Milter.factory = createMilter
      flags = Milter.CHGBODY
      Milter.set_flags(flags)

      Milter.runmilter('encryption-milter', args.socket, 600)

  except Exception as e:
    syslog('An error occured')
    syslog(str(e))

  syslog('Shutting down daemon')

if __name__ == '__main__':
  main()
