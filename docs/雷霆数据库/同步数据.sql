-- ============================================
-- 批量更新 MaterialUploadLog 表
-- 功能：
-- 1. 为符合条件的记录生成16位十六进制ID
-- 2. 将UploadStatus更新为4
-- 条件：
--   - CODE IN ('XY14', 'XY141')
--   - MaterialTime 包含 '2026-06-18'
--   - AssetGuid IS NULL (可选，根据需求调整)
-- ============================================

-- 1. 查看要更新多少条记录
SELECT 
    CODE,
    COUNT(*) AS 待更新记录总数,
    COUNT(CASE WHEN AssetGuid IS NULL THEN 1 END) AS 待生成ID记录数,
    COUNT(CASE WHEN UploadStatus != 4 THEN 1 END) AS 待更新状态记录数
FROM MaterialUploadLog
WHERE CODE IN ('XY14', 'XY141')
  AND MaterialTime LIKE '%2026-06-18%'
GROUP BY CODE;

-- 查看前10条记录的当前状态
SELECT 
    ID,
    CODE,
    MaterialFullName,
    MakeDate,
    AssetGuid AS 当前ID,
    UploadStatus AS 当前状态
FROM MaterialUploadLog
WHERE CODE IN ('XY14', 'XY141')
  AND MaterialTime LIKE '%2026-06-18%'
LIMIT 10;

-- 2. 开启事务
START TRANSACTION;

-- 3. 执行更新：同时设置 AssetGuid 和 UploadStatus
UPDATE MaterialUploadLog
SET 
    AssetGuid = SUBSTRING(MD5(RAND()), 1, 16),  -- 生成16位十六进制ID
    UploadStatus = 4                            -- 更新状态为4
WHERE CODE IN ('XY14', 'XY141')
  AND MaterialTime LIKE '%2026-06-18%'
   AND AssetGuid IS NULL;  -- 如果只需要更新ID为空的记录，取消注释这行

-- 4. 验证更新结果
SELECT 
    CODE,
    '更新后统计' AS 信息,
    COUNT(*) AS 总记录数,
    COUNT(AssetGuid) AS 已填充ID记录数,
    SUM(CASE WHEN AssetGuid IS NULL THEN 1 ELSE 0 END) AS 剩余空ID记录数,
    COUNT(CASE WHEN UploadStatus = 4 THEN 1 END) AS 状态已更新记录数,
    COUNT(CASE WHEN UploadStatus != 4 THEN 1 END) AS 状态未更新记录数
FROM MaterialUploadLog
WHERE CODE IN ('XY14', 'XY141')
  AND MaterialTime LIKE '%2026-06-18%'
GROUP BY CODE;

-- 5. 查看更新后的示例数据
SELECT 
    ID,
    CODE,
    MaterialFullName,
    SUBSTRING(MaterialFullName, 1, 20) AS 物料名缩写,
    MakeDate,
    AssetGuid AS 新ID,
    LENGTH(AssetGuid) AS ID长度,
    UploadStatus AS 新状态
FROM MaterialUploadLog
WHERE CODE IN ('XY14', 'XY141')
  AND MaterialTime LIKE '%2026-06-18%'
ORDER BY CODE, ID
LIMIT 10;

-- 6. 检查ID格式
SELECT 
    CODE,
    AssetGuid,
    LENGTH(AssetGuid) AS 长度,
    CASE 
        WHEN AssetGuid REGEXP '^[0-9a-f]{16}$' THEN '✅ 格式正确'
        ELSE '❌ 格式错误' 
    END AS 格式检查
FROM MaterialUploadLog
WHERE CODE IN ('XY14', 'XY141')
  AND MaterialTime LIKE '%2026-06-18%'
  AND AssetGuid IS NOT NULL
LIMIT 5;

-- 7. 提交事务（确认无误后执行）
 COMMIT;

-- 8. 如果有问题，可以回滚
-- ROLLBACK;