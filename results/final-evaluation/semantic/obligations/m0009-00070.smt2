(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x3009 (= s_7 (_ bv1 8))))
(not $x3009)))
(check-sat)
