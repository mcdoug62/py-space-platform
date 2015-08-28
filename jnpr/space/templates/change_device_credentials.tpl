{#
  Parameters used:
    - devices
        List of device objects on which credentials need to be changed.
        The object must have an attribute named 'href'
         
    - user_name
        This is name of the user for which you wish to change the password or key.
        
    - password
        This is the plaintext password that you wish to set for "user_name". This is only relevant if
        change_to is set to "CREDENTIAL"
         
    - change_to
        Must be either "CREDENTIAL" or "KEY". This parameter name is misleading. It is actually the
        authentication type and is stored in the database as one of these values.
        1. CREDENTIAL - means userID/password.  The updated user_name and password are stored in the Junos
            Space database.  If "change_on_device" is TRUE, then this userID/password is configured on the
            device.
        2. KEY - means userID and key. If the existing auth type is CREDENTIAL and is to be changed to KEY, then 
             o Auth Type is changed to "Key" in the Junos Space database, and 
             o An ssh connection is initiated to the device, and an RPC is issued to perform the change operation. 

    - change_on_device
         Must be either "True" or "False".  This indicates whether to change the user_name and password on the device, in addition to the Junos Space database.
#}
<change-credentials>
   <devices>
{%- for d in devices %}
     <device href="{{d.href}}"></device>
{%- endfor %}
   </devices>
   <user-name>{{user_name}}</user-name>
   <password>{{password}}</password>
   <change-to>{{change_to}}</change-to>
{%- if change_on_device %}
   <change-on-device>{{change_on_device|lower}}</change-on-device>
{% endif -%}
</change-credentials>
