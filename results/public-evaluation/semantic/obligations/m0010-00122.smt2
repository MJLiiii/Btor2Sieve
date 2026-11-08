(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x209 (= i_7 (_ bv1 8))))
(not $x209)))
(check-sat)
