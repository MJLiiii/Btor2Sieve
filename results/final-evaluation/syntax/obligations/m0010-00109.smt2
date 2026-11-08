(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x4047 (= i_6 (_ bv127 8))))
(not $x4047)))
(check-sat)
