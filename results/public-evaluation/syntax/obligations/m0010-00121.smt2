(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x203 (= i_7 (_ bv1 8))))
(not $x203)))
(check-sat)
