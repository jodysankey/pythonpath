
import sitemgt
import os
import shutil
import unittest
import platform


# NOT WORKING YET !!!!!
# NOT WORKING YET !!!!!

# Need to actually define the expected output and check input thoroughly checks each condition
# also possible that dictionary ordering wont be stable

if platform.system()=='Windows':
    #test_path = os.getenv("TMP") + "/SiteDescriptionTest" # TMP set to some hideous directory
    test_path = r"C:\Temp\SiteDescriptionTest"
else:
    test_path = "/tmp/SiteDescriptionTest"
    

XML_NAME = "TestCase.xml"
sd_filename = os.path.join(test_path,XML_NAME) 

SITE_DESCRIPTION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<SiteDescription xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

    <!--Start of Hosts and Users section-->
    <!--Start of Hosts and Users section-->
    <!--Start of Hosts and Users section-->
    <Actors>
        <Host name="server1" purpose="Server" os="Debian"/>
        <Host name="client1" purpose="First client" os="Ubuntu"/>
        <Host name="client2" purpose="Second client" os="Ubuntu"/>
        <Host name="client3" purpose="Third client" os="WindowsXP"/>
        <HostGroup name="ubuntu" description="All Ubuntu clients">
            <Member name="client1"/>
            <Member name="client2"/>
        </HostGroup>
        <User name="user1" type="Human" email="one@fictional.com"/>
        <User name="user2" type="Human" email="two@fictional.com"/>
        <User name="guest" type="Human"/>
        <User name="root" type="Role" email="root@fictional.com"/>
        <User name="sysUser1" type="System"/>
        <UserGroup name="humans" description="All humans">
            <Member name="user1"/>
            <Member name="user2"/>
            <Member name="guest"/>
        </UserGroup>
    </Actors>

    <!--Start of Capability and Requirements section-->
    <!--Start of Capability and Requirements section-->
    <!--Start of Capability and Requirements section-->
    <Functionality>
        <Capability name="Webcam" description="Capture, post, and store pictures from the webcam">
            <SystemRequirement uid="S001" text="% shall post a webcam image every 2 minutes" importance="3">
                <Requirement uid="H001"/>
                <Requirement uid="H002"/>
            </SystemRequirement>
            <SystemRequirement uid="S002"
                text="% shall store webcam image every 2 minutes for 3 days, and then every hour thereafter" importance="3">
                <Requirement uid="H001"/>
                <Requirement uid="H003"/>
            </SystemRequirement>
            <HostResponsibility host_set="server1" description="server1 is responsible for all webcam duties"/>
        </Capability>

        <Capability name="Time Sync" description="Synchronize all hosts to current time">
            <SystemRequirement uid="S003" text="% shall provide a local time sync service, synchronized to an atomic clock" importance="4">
                <Requirement uid="H004"/>
            </SystemRequirement>
            <SystemRequirement uid="S004" text="All hosts should synchronize time using the local service" importance="3">
                <Requirement uid="H005"/>
                <Requirement uid="H006"/>
                <Requirement uid="U001"/>
            </SystemRequirement>
            <HostResponsibility host_set="server1" description="server1 provides the time sync server"/>
            <HostResponsibility host_set="ubuntu" description="hosts in ubuntu must synchronize to the local server"/>
            <HostResponsibility host_set="client3" description="client3 must synchronize to the local server"/>
            <UserResponsibility user_set="root" description="root must verfify time sync is working"/>
        </Capability>

        <HostSet name="server1">
            <HostRequirement uid="H001" text="% shall provide a webcam image capture service">
                <Component name="webcam-app"/>
                <Component name="webcam-init"/>
                <Component name="reset-webcam"/>
            </HostRequirement>
            <HostRequirement uid="H002"
                text="% shall post a webcam image to www.jsankey.com every 2 minutes">
                <Component name="webcam-netrc"/>
                <Component name="webcam-rc"/>
            </HostRequirement>
            <HostRequirement uid="H003"
                text="% shall store webcam image every 2 minutes for 3 days, and then every hour thereafter"
                notes="The webcam package is configured to store images all images in /home/open/webcam/live, and then archive-webcam 
                is used to preserve the first image each hour after a certain age in /home/open/webcam/archive, and delete all others">
                <Component name="webcam-rc"/>
                <Component name="archive-webcam"/>
            </HostRequirement>
            <HostRequirement uid="H004"
                text="% shall provide a local time sync service, synchronized to an atomic clock">
                <Component name="ntp"/>
                <Component name="server-ntp.conf"/>
            </HostRequirement>
        </HostSet>

        <HostSet name="ubuntu">
            <HostRequirement uid="H005" text="All hosts in % shall synchronize time to the local sync service">
                <Component name="client-ntpdate"/>
            </HostRequirement>
        </HostSet>

        <HostSet name="client3">
            <HostRequirement uid="H006" text="% shall synchronize time to the local sync service">
                <Component name="windows-time-sync"/>
            </HostRequirement>
        </HostSet>
        
        <UserSet name="root">
            <UserRequirement uid="U001" text="% shall verify correct time sync operation"/>
        </UserSet>
    </Functionality>


    <!--Start of Software components section-->
    <!--Start of Software components section-->
    <!--Start of Software components section-->
    <Software>
        <ScriptingLanguages>
            <Language name="python3">
                <Application name="python3"/>
            </Language>
            <Language name="bash">
                <Application name="bash"/>
            </Language>
        </ScriptingLanguages>
        <Components default_cm_repository="oberon/site">
            <RepoApplication name="nfs-kernel-server"/>
            <RepoApplication name="python3"/>
            <RepoApplication name="bash"/>

            <!--Webcam-->
            <RepoApplication name="webcam-app" package="webcam"/>
            <ConfigurationFile name="fs-nfs-exports" cm_location="oberon/etc" cm_filename="exports" notes="NFS shares configuration">
                <Deployment host_set="server1" directory="/etc"/>
            </ConfigurationFile>
            <ConfigurationFile name="webcam-rc" cm_location="oberon/webcam" cm_filename="webcamrc" notes="Configures intervals and storage location for webcam">
                <Deployment host_set="server1" directory="/etc/webcam" filename=".webcamrc"/>
            </ConfigurationFile>
            <ConfigurationFile name="webcam-netrc" cm_location="oberon/webcam" cm_filename="netrc" notes="Configures FTP storage location for webcam">
                <Deployment host_set="server1" directory="/etc/webcam" filename=".netrc"/>
            </ConfigurationFile>
            <Script name="webcam-init" cm_location="oberon/init" cm_filename="webcamd" language="bash" status="working">
                <Deployment host_set="server1" directory="/etc/init.d"/>
            </Script>
            <Script name="reset-webcam" cm_location="oberon/cron" language="bash" status="working" notes="Restarts webcam service to avoid crash after too many image captures">
                <Deployment host_set="server1" directory="/etc/cron.daily" filename="srv-01-reset-webcam"/>
            </Script>
            <Script name="archive-webcam" cm_location="oberon/cron" language="python3" status="working" notes="For images older than an age, moves the first for each hour and deletes the rest">
                <Deployment host_set="server1" directory="/etc/cron.daily" filename="srv-01-reset-webcam"/>
            </Script>

            <!--Time Sync-->
            <RepoApplication name="ntp"/>
            <ConfigurationFile name="server-ntp.conf" cm_location="oberon/etc" notes="NTP time server configuration" cm_filename="ntp.conf">
                <Deployment host_set="server1" directory="/etc"/>
            </ConfigurationFile>
            <ConfigurationFile name="client-ntpdate" cm_location="kubuntu/etc" cm_filename="ntpdate" notes="Ubuntu NTP time client FTP configuration">
                <Deployment host_set="ubuntu" directory="/etc/default"/>
            </ConfigurationFile>
            <NonRepoApplication name="windows-time-sync" installationType="exe" installLocation="C:\Program Files\TimeSync" vendor="fictional"/>
        </Components>
    </Software>
</SiteDescription>
"""


class SiteDescriptionTestCase(unittest.TestCase):

    def setUp(self):

        #Make sure test directory is fresh
        if os.path.isdir(test_path):
            shutil.rmtree(test_path)
        os.mkdir(test_path)

        #Create our standard input XML in the test directory
        f = open(sd_filename,'w')
        f.write(SITE_DESCRIPTION_XML)
        f.close()


    def testConstruction (self):
        """Just verify the string representation for the entire site matches the expectation"""
        
        sd = sitemgt.SiteDescription(sd_filename)
        result_string = str(sd)

        f_actual = open(os.path.join(test_path,"actual.txt"),'w')
        f_actual.write(result_string)
        f_actual.close()
        
        #self.failUnlessEqual(result,target,"Structure 1 - Did not return correct list")

        

if __name__ == "__main__": 
    
    # This way of running allows quick focus on a particular test by entering the number, or all
    # tests by just entering "test" 
    ldr = unittest.TestLoader()
    
    #ldr.testMethodPrefix = "testStructureOne"
    ldr.testMethodPrefix = "test"
    
    suite = ldr.loadTestsFromTestCase(SiteDescriptionTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)


