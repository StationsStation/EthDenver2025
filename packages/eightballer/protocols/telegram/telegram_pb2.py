"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0etelegram.proto\x12\x1faea.eightballer.telegram.v0_1_0"\xde\n\n\x0fTelegramMessage\x12T\n\x05error\x18\x05 \x01(\x0b2C.aea.eightballer.telegram.v0_1_0.TelegramMessage.Error_PerformativeH\x00\x12b\n\x0cmessage_sent\x18\x06 \x01(\x0b2J.aea.eightballer.telegram.v0_1_0.TelegramMessage.Message_Sent_PerformativeH\x00\x12`\n\x0bnew_message\x18\x07 \x01(\x0b2I.aea.eightballer.telegram.v0_1_0.TelegramMessage.New_Message_PerformativeH\x00\x12h\n\x0freceive_message\x18\x08 \x01(\x0b2M.aea.eightballer.telegram.v0_1_0.TelegramMessage.Receive_Message_PerformativeH\x00\x12b\n\x0csend_message\x18\t \x01(\x0b2J.aea.eightballer.telegram.v0_1_0.TelegramMessage.Send_Message_PerformativeH\x00\x1a\xba\x01\n\tErrorCode\x12\\\n\nerror_code\x18\x01 \x01(\x0e2H.aea.eightballer.telegram.v0_1_0.TelegramMessage.ErrorCode.ErrorCodeEnum"O\n\rErrorCodeEnum\x12\x13\n\x0fUNKNOWN_CHAT_ID\x10\x00\x12\r\n\tAPI_ERROR\x10\x01\x12\x1a\n\x16INVALID_MESSAGE_FORMAT\x10\x02\x1a\x9c\x01\n\x19Send_Message_Performative\x12\x0f\n\x07chat_id\x18\x01 \x01(\x05\x12\x0c\n\x04text\x18\x02 \x01(\t\x12\x12\n\nparse_mode\x18\x03 \x01(\t\x12\x19\n\x11parse_mode_is_set\x18\x04 \x01(\x08\x12\x14\n\x0creply_markup\x18\x05 \x01(\t\x12\x1b\n\x13reply_markup_is_set\x18\x06 \x01(\x08\x1a;\n\x1cReceive_Message_Performative\x12\x0f\n\x07chat_id\x18\x01 \x01(\x05\x12\n\n\x02id\x18\x02 \x01(\x05\x1a7\n\x19Message_Sent_Performative\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0e\n\x06status\x18\x02 \x01(\t\x1ak\n\x18New_Message_Performative\x12\x0f\n\x07chat_id\x18\x01 \x01(\x05\x12\n\n\x02id\x18\x02 \x01(\x05\x12\x0c\n\x04text\x18\x03 \x01(\t\x12\x11\n\tfrom_user\x18\x04 \x01(\t\x12\x11\n\ttimestamp\x18\x05 \x01(\x05\x1a\x91\x02\n\x12Error_Performative\x12N\n\nerror_code\x18\x01 \x01(\x0b2:.aea.eightballer.telegram.v0_1_0.TelegramMessage.ErrorCode\x12\x11\n\terror_msg\x18\x02 \x01(\t\x12f\n\nerror_data\x18\x03 \x03(\x0b2R.aea.eightballer.telegram.v0_1_0.TelegramMessage.Error_Performative.ErrorDataEntry\x1a0\n\x0eErrorDataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x0c:\x028\x01B\x0e\n\x0cperformativeb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'telegram_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_TELEGRAMMESSAGE_ERROR_PERFORMATIVE_ERRORDATAENTRY']._loaded_options = None
    _globals['_TELEGRAMMESSAGE_ERROR_PERFORMATIVE_ERRORDATAENTRY']._serialized_options = b'8\x01'
    _globals['_TELEGRAMMESSAGE']._serialized_start = 52
    _globals['_TELEGRAMMESSAGE']._serialized_end = 1426
    _globals['_TELEGRAMMESSAGE_ERRORCODE']._serialized_start = 562
    _globals['_TELEGRAMMESSAGE_ERRORCODE']._serialized_end = 748
    _globals['_TELEGRAMMESSAGE_ERRORCODE_ERRORCODEENUM']._serialized_start = 669
    _globals['_TELEGRAMMESSAGE_ERRORCODE_ERRORCODEENUM']._serialized_end = 748
    _globals['_TELEGRAMMESSAGE_SEND_MESSAGE_PERFORMATIVE']._serialized_start = 751
    _globals['_TELEGRAMMESSAGE_SEND_MESSAGE_PERFORMATIVE']._serialized_end = 907
    _globals['_TELEGRAMMESSAGE_RECEIVE_MESSAGE_PERFORMATIVE']._serialized_start = 909
    _globals['_TELEGRAMMESSAGE_RECEIVE_MESSAGE_PERFORMATIVE']._serialized_end = 968
    _globals['_TELEGRAMMESSAGE_MESSAGE_SENT_PERFORMATIVE']._serialized_start = 970
    _globals['_TELEGRAMMESSAGE_MESSAGE_SENT_PERFORMATIVE']._serialized_end = 1025
    _globals['_TELEGRAMMESSAGE_NEW_MESSAGE_PERFORMATIVE']._serialized_start = 1027
    _globals['_TELEGRAMMESSAGE_NEW_MESSAGE_PERFORMATIVE']._serialized_end = 1134
    _globals['_TELEGRAMMESSAGE_ERROR_PERFORMATIVE']._serialized_start = 1137
    _globals['_TELEGRAMMESSAGE_ERROR_PERFORMATIVE']._serialized_end = 1410
    _globals['_TELEGRAMMESSAGE_ERROR_PERFORMATIVE_ERRORDATAENTRY']._serialized_start = 1362
    _globals['_TELEGRAMMESSAGE_ERROR_PERFORMATIVE_ERRORDATAENTRY']._serialized_end = 1410