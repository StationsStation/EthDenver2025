"""Generated protocol buffer code."""
from google.protobuf import (
    descriptor as _descriptor,
    descriptor_pool as _descriptor_pool,
    symbol_database as _symbol_database,
)
from google.protobuf.internal import builder as _builder


_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0echatroom.proto\x12\x1faea.eightballer.chatroom.v0_1_0"\xfb\x0f\n\x0fChatroomMessage\x12Z\n\x08channels\x18\x05 \x01(\x0b2F.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Channels_PerformativeH\x00\x12T\n\x05error\x18\x06 \x01(\x0b2C.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Error_PerformativeH\x00\x12b\n\x0cget_channels\x18\x07 \x01(\x0b2J.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Get_Channels_PerformativeH\x00\x12X\n\x07message\x18\x08 \x01(\x0b2E.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Message_PerformativeH\x00\x12b\n\x0cmessage_sent\x18\t \x01(\x0b2J.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Message_Sent_PerformativeH\x00\x12\\\n\tsubscribe\x18\n \x01(\x0b2G.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Subscribe_PerformativeH\x00\x12p\n\x13subscription_result\x18\x0b \x01(\x0b2Q.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Subscription_Result_PerformativeH\x00\x12`\n\x0bunsubscribe\x18\x0c \x01(\x0b2I.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Unsubscribe_PerformativeH\x00\x12t\n\x15unsubscription_result\x18\r \x01(\x0b2S.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Unsubscription_Result_PerformativeH\x00\x1a\xba\x01\n\tErrorCode\x12\\\n\nerror_code\x18\x01 \x01(\x0e2H.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.ErrorCode.ErrorCodeEnum"O\n\rErrorCodeEnum\x12\x13\n\x0fUNKNOWN_CHAT_ID\x10\x00\x12\r\n\tAPI_ERROR\x10\x01\x12\x1a\n\x16INVALID_MESSAGE_FORMAT\x10\x02\x1a\x90\x02\n\x14Message_Performative\x12\x0f\n\x07chat_id\x18\x01 \x01(\t\x12\x0c\n\x04text\x18\x02 \x01(\t\x12\n\n\x02id\x18\x03 \x01(\x05\x12\x11\n\tid_is_set\x18\x04 \x01(\x08\x12\x12\n\nparse_mode\x18\x05 \x01(\t\x12\x19\n\x11parse_mode_is_set\x18\x06 \x01(\x08\x12\x14\n\x0creply_markup\x18\x07 \x01(\t\x12\x1b\n\x13reply_markup_is_set\x18\x08 \x01(\x08\x12\x11\n\tfrom_user\x18\t \x01(\t\x12\x18\n\x10from_user_is_set\x18\n \x01(\x08\x12\x11\n\ttimestamp\x18\x0b \x01(\x05\x12\x18\n\x10timestamp_is_set\x18\x0c \x01(\x08\x1a:\n\x19Message_Sent_Performative\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x11\n\tid_is_set\x18\x02 \x01(\x08\x1a\x91\x02\n\x12Error_Performative\x12N\n\nerror_code\x18\x01 \x01(\x0b2:.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.ErrorCode\x12\x11\n\terror_msg\x18\x02 \x01(\t\x12f\n\nerror_data\x18\x03 \x03(\x0b2R.aea.eightballer.chatroom.v0_1_0.ChatroomMessage.Error_Performative.ErrorDataEntry\x1a0\n\x0eErrorDataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x0c:\x028\x01\x1a)\n\x16Subscribe_Performative\x12\x0f\n\x07chat_id\x18\x01 \x01(\t\x1a+\n\x18Unsubscribe_Performative\x12\x0f\n\x07chat_id\x18\x01 \x01(\t\x1a-\n\x19Get_Channels_Performative\x12\x10\n\x08agent_id\x18\x01 \x01(\t\x1aE\n"Unsubscription_Result_Performative\x12\x0f\n\x07chat_id\x18\x01 \x01(\t\x12\x0e\n\x06status\x18\x02 \x01(\t\x1aC\n Subscription_Result_Performative\x12\x0f\n\x07chat_id\x18\x01 \x01(\t\x12\x0e\n\x06status\x18\x02 \x01(\t\x1a)\n\x15Channels_Performative\x12\x10\n\x08channels\x18\x01 \x03(\tB\x0e\n\x0cperformativeb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'chatroom_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_CHATROOMMESSAGE_ERROR_PERFORMATIVE_ERRORDATAENTRY']._loaded_options = None
    _globals['_CHATROOMMESSAGE_ERROR_PERFORMATIVE_ERRORDATAENTRY']._serialized_options = b'8\x01'
    _globals['_CHATROOMMESSAGE']._serialized_start = 52
    _globals['_CHATROOMMESSAGE']._serialized_end = 2095
    _globals['_CHATROOMMESSAGE_ERRORCODE']._serialized_start = 964
    _globals['_CHATROOMMESSAGE_ERRORCODE']._serialized_end = 1150
    _globals['_CHATROOMMESSAGE_ERRORCODE_ERRORCODEENUM']._serialized_start = 1071
    _globals['_CHATROOMMESSAGE_ERRORCODE_ERRORCODEENUM']._serialized_end = 1150
    _globals['_CHATROOMMESSAGE_MESSAGE_PERFORMATIVE']._serialized_start = 1153
    _globals['_CHATROOMMESSAGE_MESSAGE_PERFORMATIVE']._serialized_end = 1425
    _globals['_CHATROOMMESSAGE_MESSAGE_SENT_PERFORMATIVE']._serialized_start = 1427
    _globals['_CHATROOMMESSAGE_MESSAGE_SENT_PERFORMATIVE']._serialized_end = 1485
    _globals['_CHATROOMMESSAGE_ERROR_PERFORMATIVE']._serialized_start = 1488
    _globals['_CHATROOMMESSAGE_ERROR_PERFORMATIVE']._serialized_end = 1761
    _globals['_CHATROOMMESSAGE_ERROR_PERFORMATIVE_ERRORDATAENTRY']._serialized_start = 1713
    _globals['_CHATROOMMESSAGE_ERROR_PERFORMATIVE_ERRORDATAENTRY']._serialized_end = 1761
    _globals['_CHATROOMMESSAGE_SUBSCRIBE_PERFORMATIVE']._serialized_start = 1763
    _globals['_CHATROOMMESSAGE_SUBSCRIBE_PERFORMATIVE']._serialized_end = 1804
    _globals['_CHATROOMMESSAGE_UNSUBSCRIBE_PERFORMATIVE']._serialized_start = 1806
    _globals['_CHATROOMMESSAGE_UNSUBSCRIBE_PERFORMATIVE']._serialized_end = 1849
    _globals['_CHATROOMMESSAGE_GET_CHANNELS_PERFORMATIVE']._serialized_start = 1851
    _globals['_CHATROOMMESSAGE_GET_CHANNELS_PERFORMATIVE']._serialized_end = 1896
    _globals['_CHATROOMMESSAGE_UNSUBSCRIPTION_RESULT_PERFORMATIVE']._serialized_start = 1898
    _globals['_CHATROOMMESSAGE_UNSUBSCRIPTION_RESULT_PERFORMATIVE']._serialized_end = 1967
    _globals['_CHATROOMMESSAGE_SUBSCRIPTION_RESULT_PERFORMATIVE']._serialized_start = 1969
    _globals['_CHATROOMMESSAGE_SUBSCRIPTION_RESULT_PERFORMATIVE']._serialized_end = 2036
    _globals['_CHATROOMMESSAGE_CHANNELS_PERFORMATIVE']._serialized_start = 2038
    _globals['_CHATROOMMESSAGE_CHANNELS_PERFORMATIVE']._serialized_end = 2079