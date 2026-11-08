(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x38 (= s_6 (_ bv1 4))))
(not $x38)))
(check-sat)
