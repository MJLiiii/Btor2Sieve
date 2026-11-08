(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x722 (bvuge s_4 (_ bv8 4))))
(not $x722)))
(check-sat)
