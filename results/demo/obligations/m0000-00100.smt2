(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x106 (bvuge s_5 (_ bv128 8))))
(not $x106)))
(check-sat)
