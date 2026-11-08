(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x32 (bvsge s_5 (_ bv0 8))))
(not $x32)))
(check-sat)
