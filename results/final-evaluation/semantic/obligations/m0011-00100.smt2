(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x1170 (= s_6 (_ bv1 4))))
(not $x1170)))
(check-sat)
